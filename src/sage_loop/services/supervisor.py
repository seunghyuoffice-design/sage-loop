"""
Sage Supervisor - 백그라운드 감독 루프

기능:
    - 활성 세션 모니터링 (5초 간격)
    - 정체 세션 감지 (5분 이상)
    - SSE 구독자 관리 및 브로드캐스트
    - 자동 복구 시도

Dashboard의 MetricsCollector 패턴 차용.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from ..adapters.redis_adapter import RedisAdapter
from ..config import get_settings
from ..schemas import SessionStatus

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스
_supervisor: Optional["Supervisor"] = None


class Supervisor:
    """Sage 감독 루프"""

    def __init__(self):
        settings = get_settings()
        self.monitor_interval = settings.supervisor.monitor_interval
        self.stall_threshold = settings.supervisor.stall_threshold
        self.max_subscribers = settings.supervisor.max_subscribers

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._subscribers: list[asyncio.Queue] = []
        self._active_sessions: dict[str, dict[str, Any]] = {}
        self._last_activity: dict[str, datetime] = {}

        self.redis = RedisAdapter()

    # ═══════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════

    async def start(self) -> None:
        """감독 루프 시작"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Supervisor started (interval: {self.monitor_interval}s, " f"stall: {self.stall_threshold}s)")

    async def stop(self) -> None:
        """감독 루프 중지"""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # 구독자 정리
        self._subscribers.clear()
        logger.info("Supervisor stopped")

    async def _run_loop(self) -> None:
        """무한 감독 루프"""
        while self._running:
            try:
                await self._monitor_sessions()
                await self._detect_stalls()
            except Exception as e:
                logger.error(f"Supervisor error: {e}")

            await asyncio.sleep(self.monitor_interval)

    # ═══════════════════════════════════════════════════════════════
    # Session Monitoring
    # ═══════════════════════════════════════════════════════════════

    async def _monitor_sessions(self) -> None:
        """활성 세션 모니터링"""
        try:
            sessions = await self.redis.get_active_sessions()

            for session_id, session_data in sessions.items():
                # 상태 변경 감지
                old_state = self._active_sessions.get(session_id)

                if old_state != session_data:
                    # 변경 이벤트 브로드캐스트
                    await self._broadcast(
                        {
                            "type": "session_update",
                            "session_id": session_id,
                            "state": session_data,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                    # 역할 변경 감지
                    if old_state:
                        old_role = old_state.get("current_role")
                        new_role = session_data.get("current_role")

                        if old_role != new_role and new_role:
                            await self._broadcast(
                                {
                                    "type": "role_change",
                                    "session_id": session_id,
                                    "from_role": old_role,
                                    "to_role": new_role,
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            )

                    # 활동 시간 업데이트
                    self._last_activity[session_id] = datetime.utcnow()

                self._active_sessions[session_id] = session_data

            # 종료된 세션 정리
            current_ids = set(sessions.keys())
            cached_ids = set(self._active_sessions.keys())

            for session_id in cached_ids - current_ids:
                del self._active_sessions[session_id]
                if session_id in self._last_activity:
                    del self._last_activity[session_id]

        except Exception as e:
            logger.warning(f"Session monitoring failed: {e}")

    async def _detect_stalls(self) -> None:
        """정체 세션 감지"""
        now = datetime.utcnow()

        for session_id, session_data in self._active_sessions.items():
            status = session_data.get("status")

            # 실행 중인 세션만 체크
            if status != SessionStatus.EXECUTING.value:
                continue

            last_activity = self._last_activity.get(session_id)
            if not last_activity:
                continue

            elapsed = (now - last_activity).total_seconds()

            if elapsed > self.stall_threshold:
                logger.warning(
                    f"[{session_id}] Stall detected: {elapsed:.0f}s " f"(threshold: {self.stall_threshold}s)"
                )

                await self._broadcast(
                    {
                        "type": "stall_detected",
                        "session_id": session_id,
                        "current_role": session_data.get("current_role"),
                        "elapsed_seconds": elapsed,
                        "threshold_seconds": self.stall_threshold,
                        "timestamp": now.isoformat(),
                    }
                )

    # ═══════════════════════════════════════════════════════════════
    # SSE Subscription
    # ═══════════════════════════════════════════════════════════════

    def subscribe(self) -> asyncio.Queue:
        """SSE 구독"""
        if len(self._subscribers) >= self.max_subscribers:
            # 오래된 구독자 제거
            self._subscribers.pop(0)

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        logger.debug(f"New subscriber, total: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """SSE 구독 해제"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.debug(f"Subscriber removed, total: {len(self._subscribers)}")

    async def _broadcast(self, data: dict[str, Any]) -> None:
        """모든 구독자에게 브로드캐스트"""
        if not self._subscribers:
            return

        dead_queues = []

        for queue in self._subscribers:
            try:
                # 큐가 가득 차면 오래된 데이터 제거
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass

                queue.put_nowait(data)

            except Exception:
                dead_queues.append(queue)

        # 죽은 큐 정리
        for q in dead_queues:
            if q in self._subscribers:
                self._subscribers.remove(q)

    # ═══════════════════════════════════════════════════════════════
    # Manual Operations
    # ═══════════════════════════════════════════════════════════════

    async def notify_role_start(self, session_id: str, role: str) -> None:
        """역할 시작 알림"""
        self._last_activity[session_id] = datetime.utcnow()

        await self._broadcast(
            {
                "type": "role_start",
                "session_id": session_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def notify_role_complete(self, session_id: str, role: str, success: bool = True) -> None:
        """역할 완료 알림"""
        self._last_activity[session_id] = datetime.utcnow()

        await self._broadcast(
            {
                "type": "role_complete",
                "session_id": session_id,
                "role": role,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def notify_chain_complete(self, session_id: str, success: bool = True) -> None:
        """체인 완료 알림"""
        await self._broadcast(
            {
                "type": "chain_complete",
                "session_id": session_id,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def notify_error(self, session_id: str, error: str) -> None:
        """에러 알림"""
        await self._broadcast(
            {
                "type": "error",
                "session_id": session_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    # ═══════════════════════════════════════════════════════════════
    # Status
    # ═══════════════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._running

    @property
    def subscriber_count(self) -> int:
        """구독자 수"""
        return len(self._subscribers)

    @property
    def active_session_count(self) -> int:
        """활성 세션 수"""
        return len(self._active_sessions)

    def get_stats(self) -> dict[str, Any]:
        """통계 반환"""
        return {
            "running": self._running,
            "subscribers": len(self._subscribers),
            "active_sessions": len(self._active_sessions),
            "monitor_interval": self.monitor_interval,
            "stall_threshold": self.stall_threshold,
        }


def get_supervisor() -> Supervisor:
    """싱글톤 감독자 반환"""
    global _supervisor
    if _supervisor is None:
        _supervisor = Supervisor()
    return _supervisor


def reset_supervisor() -> None:
    """감독자 리셋 (테스트용)"""
    global _supervisor
    _supervisor = None
