"""
Sage State Service - 세션 및 체인 상태 관리

세션 라이프사이클:
    pending → executing → waiting_approval → completed/failed/cancelled
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from ..adapters.redis_adapter import RedisAdapter
from ..schemas import (
    ChainType,
    ExecutionMode,
    RoleOutput,
    RoleStatus,
    SessionDetail,
    SessionStatus,
    TaskAnalysis,
)

logger = logging.getLogger(__name__)


class SessionState:
    """세션 상태 모델"""

    def __init__(
        self,
        id: str,
        user_request: str,
        chain_type: ChainType,
        mode: ExecutionMode,
        analysis: TaskAnalysis,
        status: SessionStatus = SessionStatus.PENDING,
        current_role: Optional[str] = None,
        completed_roles: Optional[list[str]] = None,
        branch_count: int = 0,
        error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_request = user_request
        self.chain_type = chain_type
        self.mode = mode
        self.analysis = analysis
        self.status = status
        self.current_role = current_role
        self.completed_roles = completed_roles or []
        self.branch_count = branch_count
        self.error = error
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "user_request": self.user_request,
            "chain_type": self.chain_type.value,
            "mode": self.mode.value,
            "analysis": self.analysis.model_dump(),
            "status": self.status.value,
            "current_role": self.current_role,
            "completed_roles": self.completed_roles,
            "branch_count": self.branch_count,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """딕셔너리에서 생성"""
        import json as _json

        # analysis 처리 (문자열이면 JSON 파싱)
        analysis = data.get("analysis", {})
        if isinstance(analysis, str):
            try:
                analysis = _json.loads(analysis)
            except _json.JSONDecodeError:
                analysis = {}
        if isinstance(analysis, dict):
            analysis = TaskAnalysis(**analysis)

        # completed_roles 처리 (문자열이면 JSON 파싱)
        completed_roles = data.get("completed_roles", [])
        if isinstance(completed_roles, str):
            completed_roles = _json.loads(completed_roles)

        return cls(
            id=data["id"],
            user_request=data.get("user_request", ""),
            chain_type=ChainType(data["chain_type"]),
            mode=ExecutionMode(data["mode"]),
            analysis=analysis,
            status=SessionStatus(data["status"]),
            current_role=data.get("current_role"),
            completed_roles=completed_roles,
            branch_count=int(data.get("branch_count", 0)),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )


class StateService:
    """세션 및 체인 상태 관리 서비스"""

    def __init__(self):
        self.redis = RedisAdapter()
        self._cache: dict[str, SessionState] = {}

    # ═══════════════════════════════════════════════════════════════
    # Session CRUD
    # ═══════════════════════════════════════════════════════════════

    async def create_session(
        self,
        user_request: str,
        chain_type: ChainType,
        mode: ExecutionMode,
        analysis: TaskAnalysis,
    ) -> SessionState:
        """새 세션 생성"""
        session_id = f"sess-{uuid.uuid4().hex[:8]}"

        session = SessionState(
            id=session_id,
            user_request=user_request,
            chain_type=chain_type,
            mode=mode,
            analysis=analysis,
            status=SessionStatus.PENDING,
        )

        # Redis 저장
        await self.redis.save_session(session_id, session.to_dict())
        await self.redis.add_to_queue("pending", session_id)

        # 캐시 저장
        self._cache[session_id] = session

        logger.info(f"Created session {session_id}: chain={chain_type}, mode={mode}")

        return session

    async def get_session(self, session_id: str) -> Optional[SessionDetail]:
        """세션 조회"""
        # 캐시 확인
        if session_id in self._cache:
            session = self._cache[session_id]
            return SessionDetail(
                id=session.id,
                status=session.status,
                mode=session.mode,
                chain_type=session.chain_type,
                current_role=session.current_role,
                analysis=session.analysis,
                created_at=session.created_at,
                updated_at=session.updated_at,
                user_request=session.user_request,
                completed_roles=session.completed_roles,
                branch_count=session.branch_count,
                error=session.error,
            )

        # Redis 조회
        data = await self.redis.get_session(session_id)
        if not data:
            return None

        session = SessionState.from_dict(data)
        self._cache[session_id] = session

        return SessionDetail(
            id=session.id,
            status=session.status,
            mode=session.mode,
            chain_type=session.chain_type,
            current_role=session.current_role,
            analysis=session.analysis,
            created_at=session.created_at,
            updated_at=session.updated_at,
            user_request=session.user_request,
            completed_roles=session.completed_roles,
            branch_count=session.branch_count,
            error=session.error,
        )

    async def update_status(
        self,
        session_id: str,
        status: SessionStatus,
        error: Optional[str] = None,
    ) -> None:
        """세션 상태 업데이트"""
        now = datetime.utcnow()

        # 이전 상태 조회
        session = self._cache.get(session_id)
        if session:
            old_status = session.status
        else:
            data = await self.redis.get_session(session_id)
            old_status = SessionStatus(data["status"]) if data else None

        # 큐 이동
        if old_status:
            await self._move_queue(session_id, old_status, status)

        # Redis 업데이트
        updates = {
            "status": status.value,
            "updated_at": now,
        }
        if error:
            updates["error"] = error

        await self.redis.update_session(session_id, updates)

        # 캐시 업데이트
        if session_id in self._cache:
            self._cache[session_id].status = status
            self._cache[session_id].updated_at = now
            if error:
                self._cache[session_id].error = error

        logger.info(f"Session {session_id} status: {old_status} → {status}")

    async def update_current_role(self, session_id: str, role: str) -> None:
        """현재 역할 업데이트"""
        now = datetime.utcnow()

        await self.redis.update_session(
            session_id,
            {
                "current_role": role,
                "updated_at": now,
            },
        )

        if session_id in self._cache:
            self._cache[session_id].current_role = role
            self._cache[session_id].updated_at = now

    async def add_completed_role(self, session_id: str, role: str) -> None:
        """완료된 역할 추가"""
        session = self._cache.get(session_id)
        if not session:
            data = await self.redis.get_session(session_id)
            if data:
                session = SessionState.from_dict(data)
                self._cache[session_id] = session

        if session:
            if role not in session.completed_roles:
                session.completed_roles.append(role)

            await self.redis.update_session(
                session_id,
                {
                    "completed_roles": session.completed_roles,
                    "updated_at": datetime.utcnow(),
                },
            )

    async def increment_branch_count(self, session_id: str) -> int:
        """분기 카운트 증가"""
        session = self._cache.get(session_id)
        if not session:
            data = await self.redis.get_session(session_id)
            if data:
                session = SessionState.from_dict(data)
                self._cache[session_id] = session

        if session:
            session.branch_count += 1

            await self.redis.update_session(
                session_id,
                {
                    "branch_count": session.branch_count,
                    "updated_at": datetime.utcnow(),
                },
            )

            return session.branch_count

        return 0

    async def _move_queue(
        self,
        session_id: str,
        old_status: SessionStatus,
        new_status: SessionStatus,
    ) -> None:
        """상태 변경에 따른 큐 이동"""
        # 이전 큐에서 제거
        if old_status == SessionStatus.PENDING:
            await self.redis.remove_from_queue("pending", session_id)
        elif old_status == SessionStatus.EXECUTING:
            await self.redis.remove_from_queue("executing", session_id)
        elif old_status == SessionStatus.WAITING_APPROVAL:
            await self.redis.remove_from_queue("waiting", session_id)

        # 새 큐에 추가
        if new_status == SessionStatus.PENDING:
            await self.redis.add_to_queue("pending", session_id)
        elif new_status == SessionStatus.EXECUTING:
            await self.redis.add_to_queue("executing", session_id)
        elif new_status == SessionStatus.WAITING_APPROVAL:
            await self.redis.add_to_queue("waiting", session_id)

    # ═══════════════════════════════════════════════════════════════
    # Role Output
    # ═══════════════════════════════════════════════════════════════

    async def save_role_output(
        self,
        session_id: str,
        role: str,
        output: dict,
        coaching: Optional[dict] = None,
    ) -> None:
        """역할 출력 저장"""
        data = {
            "role": role,
            "status": RoleStatus.COMPLETED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "output": output,
            "coaching": coaching,
        }

        await self.redis.save_role_output(session_id, role, data)

    async def get_role_output(self, session_id: str, role: str) -> Optional[RoleOutput]:
        """역할 출력 조회"""
        data = await self.redis.get_role_output(session_id, role)
        if not data:
            return None

        return RoleOutput(
            role=data["role"],
            status=RoleStatus(data["status"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            output=data.get("output"),
            coaching=data.get("coaching"),
        )

    async def get_all_role_outputs(self, session_id: str) -> dict[str, RoleOutput]:
        """세션의 모든 역할 출력 조회"""
        data = await self.redis.get_all_role_outputs(session_id)

        return {
            role: RoleOutput(
                role=output["role"],
                status=RoleStatus(output["status"]),
                completed_at=datetime.fromisoformat(output["completed_at"]) if output.get("completed_at") else None,
                output=output.get("output"),
                coaching=output.get("coaching"),
            )
            for role, output in data.items()
        }

    # ═══════════════════════════════════════════════════════════════
    # Chain State
    # ═══════════════════════════════════════════════════════════════

    async def init_chain_state(
        self,
        session_id: str,
        chain_type: ChainType,
        roles: list[str],
    ) -> None:
        """체인 상태 초기화"""
        await self.redis.save_chain_state(
            session_id,
            {
                "chain_type": chain_type.value,
                "roles": roles,
                "completed_roles": [],
                "current_role": None,
                "branch_count": 0,
                "loop_counts": {},
            },
        )

    async def get_loop_count(self, session_id: str, role: str) -> int:
        """분기 루프 카운트 조회"""
        return await self.redis.get_loop_count(session_id, role)

    async def increment_loop_count(self, session_id: str, role: str) -> int:
        """분기 루프 카운트 증가"""
        return await self.redis.increment_loop_count(session_id, role)

    # ═══════════════════════════════════════════════════════════════
    # Active Sessions
    # ═══════════════════════════════════════════════════════════════

    async def get_active_sessions(self) -> dict[str, SessionState]:
        """활성 세션 조회"""
        data = await self.redis.get_active_sessions()

        return {session_id: SessionState.from_dict(session_data) for session_id, session_data in data.items()}

    async def count_active_sessions(self) -> int:
        """활성 세션 수 조회"""
        return await self.redis.count_active_sessions()
