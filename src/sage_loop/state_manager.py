"""
Unified State Manager - CLI/API 공통 상태 관리

CLI와 API의 이중 상태 관리 문제를 해결하기 위한 추상화 레이어.

백엔드:
    - FileStateBackend: CLI용 파일 기반 (동기)
    - RedisStateBackend: API용 Redis 기반 (비동기)

사용 예시:
    # CLI
    backend = FileStateBackend(state_dir=Path("/tmp"))
    manager = UnifiedStateManager(backend)
    manager.save_sync("session-123", state_dict)

    # API
    backend = RedisStateBackend(redis_adapter)
    manager = UnifiedStateManager(backend)
    await manager.save("session-123", state_dict)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# State Backend Protocol
# =============================================================================


@runtime_checkable
class StateBackend(Protocol):
    """상태 저장소 프로토콜 (동기/비동기 모두 지원)"""

    def save_sync(self, session_id: str, state: dict[str, Any]) -> None:
        """동기 저장"""
        ...

    def load_sync(self, session_id: str) -> Optional[dict[str, Any]]:
        """동기 로드"""
        ...

    def delete_sync(self, session_id: str) -> None:
        """동기 삭제"""
        ...

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """비동기 저장"""
        ...

    async def load(self, session_id: str) -> Optional[dict[str, Any]]:
        """비동기 로드"""
        ...

    async def delete(self, session_id: str) -> None:
        """비동기 삭제"""
        ...


# =============================================================================
# File State Backend (CLI용)
# =============================================================================


class FileStateBackend:
    """파일 기반 상태 저장소 (CLI용)

    상태를 JSON 파일로 저장/로드합니다.
    원자적 쓰기(atomic write)를 사용하여 데이터 무결성을 보장합니다.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Args:
            state_dir: 상태 파일 저장 디렉토리 (기본: /tmp)
        """
        self.state_dir = state_dir or Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, session_id: str) -> Path:
        """세션 ID에 대한 파일 경로 반환"""
        return self.state_dir / f"sage_state_{session_id}.json"

    def save_sync(self, session_id: str, state: dict[str, Any]) -> None:
        """동기 저장 (원자적 쓰기)"""
        path = self._get_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 원자적 쓰기: temp -> rename
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(state, f, ensure_ascii=False, indent=2, default=str)
            os.rename(tmp_path, path)  # POSIX에서 원자적
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load_sync(self, session_id: str) -> Optional[dict[str, Any]]:
        """동기 로드"""
        path = self._get_path(session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load state for {session_id}: {e}")
            return None

    def delete_sync(self, session_id: str) -> None:
        """동기 삭제"""
        path = self._get_path(session_id)
        lock_path = path.with_suffix(".lock")
        if path.exists():
            path.unlink()
        if lock_path.exists():
            lock_path.unlink()

    # 비동기 메서드 (동기 메서드 래핑)
    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """비동기 저장 (내부적으로 동기 호출)"""
        self.save_sync(session_id, state)

    async def load(self, session_id: str) -> Optional[dict[str, Any]]:
        """비동기 로드 (내부적으로 동기 호출)"""
        return self.load_sync(session_id)

    async def delete(self, session_id: str) -> None:
        """비동기 삭제 (내부적으로 동기 호출)"""
        self.delete_sync(session_id)


# =============================================================================
# Redis State Backend (API용)
# =============================================================================


class RedisStateBackend:
    """Redis 기반 상태 저장소 (API용)

    RedisAdapter를 사용하여 상태를 Redis에 저장/로드합니다.
    """

    def __init__(self, redis_adapter: Optional[Any] = None):
        """
        Args:
            redis_adapter: RedisAdapter 인스턴스 (None이면 lazy init)
        """
        self._redis = redis_adapter
        self._initialized = False

    async def _get_redis(self):
        """Redis 어댑터 lazy init"""
        if self._redis is None and not self._initialized:
            self._initialized = True
            try:
                from .adapters.redis_adapter import RedisAdapter

                self._redis = RedisAdapter()
            except ImportError:
                logger.warning("RedisAdapter not available")
        return self._redis

    def save_sync(self, session_id: str, state: dict[str, Any]) -> None:
        """동기 저장 (Redis는 비동기이므로 미지원)"""
        raise NotImplementedError("RedisStateBackend does not support sync operations")

    def load_sync(self, session_id: str) -> Optional[dict[str, Any]]:
        """동기 로드 (Redis는 비동기이므로 미지원)"""
        raise NotImplementedError("RedisStateBackend does not support sync operations")

    def delete_sync(self, session_id: str) -> None:
        """동기 삭제 (Redis는 비동기이므로 미지원)"""
        raise NotImplementedError("RedisStateBackend does not support sync operations")

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """비동기 저장"""
        redis = await self._get_redis()
        if redis:
            await redis.save_session(session_id, state)
        else:
            logger.warning(f"Redis unavailable, state not saved: {session_id}")

    async def load(self, session_id: str) -> Optional[dict[str, Any]]:
        """비동기 로드"""
        redis = await self._get_redis()
        if redis:
            return await redis.get_session(session_id)
        return None

    async def delete(self, session_id: str) -> None:
        """비동기 삭제"""
        redis = await self._get_redis()
        if redis:
            await redis.delete_session(session_id)


# =============================================================================
# Unified State Manager
# =============================================================================


class UnifiedStateManager:
    """CLI/API 공통 상태 관리자

    백엔드에 따라 파일 또는 Redis에 상태를 저장합니다.
    동일한 인터페이스로 CLI와 API 모두에서 사용 가능합니다.

    Example:
        # CLI용 (동기)
        manager = UnifiedStateManager(FileStateBackend())
        manager.save_sync("sess-123", {"status": "running"})

        # API용 (비동기)
        manager = UnifiedStateManager(RedisStateBackend())
        await manager.save("sess-123", {"status": "running"})
    """

    def __init__(self, backend: StateBackend):
        """
        Args:
            backend: StateBackend 구현체
        """
        self.backend = backend

    # 동기 메서드 (CLI용)
    def save_sync(self, session_id: str, state: dict[str, Any]) -> None:
        """동기 저장"""
        self.backend.save_sync(session_id, state)

    def load_sync(self, session_id: str) -> Optional[dict[str, Any]]:
        """동기 로드"""
        return self.backend.load_sync(session_id)

    def delete_sync(self, session_id: str) -> None:
        """동기 삭제"""
        self.backend.delete_sync(session_id)

    # 비동기 메서드 (API용)
    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        """비동기 저장"""
        await self.backend.save(session_id, state)

    async def load(self, session_id: str) -> Optional[dict[str, Any]]:
        """비동기 로드"""
        return await self.backend.load(session_id)

    async def delete(self, session_id: str) -> None:
        """비동기 삭제"""
        await self.backend.delete(session_id)


# =============================================================================
# Factory Functions
# =============================================================================


def get_file_state_manager(state_dir: Optional[Path] = None) -> UnifiedStateManager:
    """파일 기반 상태 관리자 생성 (CLI용)"""
    return UnifiedStateManager(FileStateBackend(state_dir))


def get_redis_state_manager() -> UnifiedStateManager:
    """Redis 기반 상태 관리자 생성 (API용)"""
    return UnifiedStateManager(RedisStateBackend())
