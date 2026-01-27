"""
Sage Redis Adapter - 세션 및 체인 상태 저장

Redis 스키마:
    sage:session:{id}       → 세션 상태 (Hash)
    sage:chain:{id}         → 체인 실행 상태 (Hash)
    sage:role:{id}:{role}   → 역할별 출력 (String/JSON)
    sage:queue:pending      → 대기 중 세션 (List)
    sage:queue:executing    → 실행 중 세션 (Set)
    sage:queue:waiting      → 승인 대기 세션 (Set)

Fallback: Redis 연결 실패 시 메모리 모드로 동작
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from ..config import get_settings

logger = logging.getLogger(__name__)

# Redis import (optional)
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None


def _serialize_for_redis(data: dict[str, Any]) -> dict[str, Any]:
    """Redis HSET용 데이터 직렬화.

    None, list, dict, bool, datetime을 Redis 호환 타입으로 변환.
    """
    processed = {}
    for k, v in data.items():
        if v is None:
            processed[k] = ""  # None → 빈 문자열
        elif isinstance(v, datetime):
            processed[k] = v.isoformat()
        elif isinstance(v, (dict, list)):
            processed[k] = json.dumps(v)
        elif isinstance(v, bool):
            processed[k] = str(v).lower()  # bool → "true"/"false"
        else:
            processed[k] = v
    return processed


def _deserialize_from_redis(
    data: dict[Any, Any], json_fields: list[str] | None = None
) -> dict[str, Any]:
    """Redis HGETALL 결과 역직렬화.

    bytes 디코딩, 빈 문자열→None, bool 문자열→bool, JSON 필드 파싱.
    """
    if json_fields is None:
        json_fields = []

    result = {}
    for k, v in data.items():
        # bytes 디코딩
        key_str = k.decode() if isinstance(k, bytes) else k
        val = v.decode() if isinstance(v, bytes) else v

        # 빈 문자열 → None 복원
        if val == "":
            result[key_str] = None
        # bool 복원
        elif val == "true":
            result[key_str] = True
        elif val == "false":
            result[key_str] = False
        # JSON 필드 파싱
        elif key_str in json_fields:
            try:
                result[key_str] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                result[key_str] = val
        else:
            result[key_str] = val

    return result


class InMemoryStore:
    """메모리 기반 저장소 (Redis fallback)"""

    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.chains: dict[str, dict] = {}
        self.roles: dict[str, dict] = {}
        self.queues: dict[str, list] = {
            "pending": [],
            "executing": [],
            "waiting": [],
        }


# 글로벌 메모리 저장소
_memory_store: Optional[InMemoryStore] = None


def get_memory_store() -> InMemoryStore:
    """메모리 저장소 반환"""
    global _memory_store
    if _memory_store is None:
        _memory_store = InMemoryStore()
    return _memory_store


class RedisAdapter:
    """Sage Redis 어댑터 (메모리 fallback 지원)"""

    # Key 프리픽스
    PREFIX = "sage"
    SESSION_KEY = f"{PREFIX}:session"
    CHAIN_KEY = f"{PREFIX}:chain"
    ROLE_KEY = f"{PREFIX}:role"
    QUEUE_PENDING = f"{PREFIX}:queue:pending"
    QUEUE_EXECUTING = f"{PREFIX}:queue:executing"
    QUEUE_WAITING = f"{PREFIX}:queue:waiting"

    def __init__(self):
        self._client: Optional[Redis] = None
        self._use_memory = not REDIS_AVAILABLE
        self._memory = get_memory_store()
        self._connection_tested = False

    async def _get_client(self) -> Optional[Redis]:
        """Redis 클라이언트 반환 (lazy init, fallback to memory)"""
        if self._use_memory:
            return None

        if self._client is None and not self._connection_tested:
            self._connection_tested = True
            try:
                settings = get_settings()
                self._client = redis.Redis(
                    host=settings.redis.host,
                    port=settings.redis.port,
                    db=settings.redis.db,
                    password=settings.redis.password,
                    decode_responses=True,
                )
                # 연결 테스트
                await self._client.ping()
                logger.info("Redis connected")
            except Exception as e:
                # SAGE_REQUIRE_REDIS=1 설정 시 Redis 필수
                if os.environ.get("SAGE_REQUIRE_REDIS", "0") == "1":
                    raise RuntimeError(f"Redis connection required but failed: {e}")
                logger.warning(f"Redis connection failed, using memory mode (data will not persist): {e}")
                self._use_memory = True
                self._client = None

        return self._client

    async def close(self):
        """연결 종료"""
        if self._client:
            await self._client.close()
            self._client = None

    # ═══════════════════════════════════════════════════════════════
    # Session Operations
    # ═══════════════════════════════════════════════════════════════

    async def save_session(self, session_id: str, data: dict[str, Any]) -> None:
        """세션 저장"""
        processed = _serialize_for_redis(data)

        client = await self._get_client()
        if client:
            key = f"{self.SESSION_KEY}:{session_id}"
            await client.hset(key, mapping=processed)
            await client.expire(key, 86400)
        else:
            # 메모리 모드
            self._memory.sessions[session_id] = processed

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """세션 조회"""
        client = await self._get_client()

        if client:
            key = f"{self.SESSION_KEY}:{session_id}"
            data = await client.hgetall(key)
        else:
            # 메모리 모드
            data = self._memory.sessions.get(session_id)

        if not data:
            return None

        return _deserialize_from_redis(data, json_fields=["analysis", "completed_roles"])

    async def update_session(self, session_id: str, updates: dict[str, Any]) -> None:
        """세션 업데이트"""
        processed = _serialize_for_redis(updates)

        client = await self._get_client()
        if client:
            key = f"{self.SESSION_KEY}:{session_id}"
            await client.hset(key, mapping=processed)
        else:
            # 메모리 모드
            if session_id in self._memory.sessions:
                self._memory.sessions[session_id].update(processed)

    async def delete_session(self, session_id: str) -> None:
        """세션 삭제"""
        client = await self._get_client()

        if client:
            keys_to_delete = [
                f"{self.SESSION_KEY}:{session_id}",
                f"{self.CHAIN_KEY}:{session_id}",
            ]
            role_pattern = f"{self.ROLE_KEY}:{session_id}:*"
            role_keys = await client.keys(role_pattern)
            keys_to_delete.extend(role_keys)
            if keys_to_delete:
                await client.delete(*keys_to_delete)
        else:
            # 메모리 모드
            self._memory.sessions.pop(session_id, None)
            self._memory.chains.pop(session_id, None)
            # 역할 출력 삭제
            to_delete = [k for k in self._memory.roles if k.startswith(f"{session_id}:")]
            for k in to_delete:
                del self._memory.roles[k]

    # ═══════════════════════════════════════════════════════════════
    # Chain Operations
    # ═══════════════════════════════════════════════════════════════

    async def save_chain_state(self, session_id: str, data: dict[str, Any]) -> None:
        """체인 상태 저장"""
        processed = _serialize_for_redis(data)

        client = await self._get_client()
        if client:
            key = f"{self.CHAIN_KEY}:{session_id}"
            await client.hset(key, mapping=processed)
            await client.expire(key, 86400)
        else:
            # 메모리 모드
            self._memory.chains[session_id] = processed

    async def get_chain_state(self, session_id: str) -> Optional[dict[str, Any]]:
        """체인 상태 조회"""
        client = await self._get_client()

        if client:
            key = f"{self.CHAIN_KEY}:{session_id}"
            data = await client.hgetall(key)
        else:
            # 메모리 모드
            data = self._memory.chains.get(session_id)

        if not data:
            return None

        return _deserialize_from_redis(data, json_fields=["roles", "completed_roles", "loop_counts"])

    async def update_chain_state(self, session_id: str, updates: dict[str, Any]) -> None:
        """체인 상태 업데이트"""
        processed = _serialize_for_redis(updates)

        client = await self._get_client()
        if client:
            key = f"{self.CHAIN_KEY}:{session_id}"
            await client.hset(key, mapping=processed)
        else:
            # 메모리 모드
            if session_id in self._memory.chains:
                self._memory.chains[session_id].update(processed)

    # ═══════════════════════════════════════════════════════════════
    # Role Output Operations
    # ═══════════════════════════════════════════════════════════════

    async def save_role_output(self, session_id: str, role: str, data: dict[str, Any]) -> None:
        """역할 출력 저장"""
        client = await self._get_client()

        if client:
            key = f"{self.ROLE_KEY}:{session_id}:{role}"
            await client.set(key, json.dumps(data, default=str))
            await client.expire(key, 86400)
        else:
            # 메모리 모드
            self._memory.roles[f"{session_id}:{role}"] = data

    async def get_role_output(self, session_id: str, role: str) -> Optional[dict[str, Any]]:
        """역할 출력 조회"""
        client = await self._get_client()

        if client:
            key = f"{self.ROLE_KEY}:{session_id}:{role}"
            data = await client.get(key)
            if not data:
                return None
            # bytes → str 디코딩 후 JSON 파싱
            data_str = data.decode() if isinstance(data, bytes) else data
            return json.loads(data_str)
        else:
            # 메모리 모드
            return self._memory.roles.get(f"{session_id}:{role}")

    async def get_all_role_outputs(self, session_id: str) -> dict[str, dict[str, Any]]:
        """세션의 모든 역할 출력 조회"""
        client = await self._get_client()

        if client:
            pattern = f"{self.ROLE_KEY}:{session_id}:*"
            keys = await client.keys(pattern)
            if not keys:
                return {}

            result = {}
            for key in keys:
                # bytes → str 디코딩
                key_str = key.decode() if isinstance(key, bytes) else key
                role = key_str.split(":")[-1]
                data = await client.get(key)
                if data:
                    # bytes → str 디코딩 후 JSON 파싱
                    data_str = data.decode() if isinstance(data, bytes) else data
                    result[role] = json.loads(data_str)
            return result
        else:
            # 메모리 모드
            result = {}
            prefix = f"{session_id}:"
            for key, data in self._memory.roles.items():
                if key.startswith(prefix):
                    role = key[len(prefix) :]
                    result[role] = data
            return result

    # ═══════════════════════════════════════════════════════════════
    # Queue Operations
    # ═══════════════════════════════════════════════════════════════

    async def add_to_queue(self, queue_name: str, session_id: str) -> None:
        """큐에 세션 추가"""
        client = await self._get_client()

        if client:
            if queue_name == "pending":
                await client.rpush(self.QUEUE_PENDING, session_id)
            elif queue_name == "executing":
                await client.sadd(self.QUEUE_EXECUTING, session_id)
            elif queue_name == "waiting":
                await client.sadd(self.QUEUE_WAITING, session_id)
        else:
            # 메모리 모드
            if session_id not in self._memory.queues[queue_name]:
                self._memory.queues[queue_name].append(session_id)

    async def remove_from_queue(self, queue_name: str, session_id: str) -> None:
        """큐에서 세션 제거"""
        client = await self._get_client()

        if client:
            if queue_name == "pending":
                await client.lrem(self.QUEUE_PENDING, 0, session_id)
            elif queue_name == "executing":
                await client.srem(self.QUEUE_EXECUTING, session_id)
            elif queue_name == "waiting":
                await client.srem(self.QUEUE_WAITING, session_id)
        else:
            # 메모리 모드
            if session_id in self._memory.queues[queue_name]:
                self._memory.queues[queue_name].remove(session_id)

    async def get_queue_sessions(self, queue_name: str) -> list[str]:
        """큐의 세션 목록 조회"""
        client = await self._get_client()

        if client:
            if queue_name == "pending":
                return await client.lrange(self.QUEUE_PENDING, 0, -1)
            elif queue_name == "executing":
                return list(await client.smembers(self.QUEUE_EXECUTING))
            elif queue_name == "waiting":
                return list(await client.smembers(self.QUEUE_WAITING))
            return []
        else:
            # 메모리 모드
            return list(self._memory.queues.get(queue_name, []))

    async def get_queue_counts(self) -> dict[str, int]:
        """큐별 세션 수 조회"""
        client = await self._get_client()

        if client:
            return {
                "pending": await client.llen(self.QUEUE_PENDING),
                "executing": await client.scard(self.QUEUE_EXECUTING),
                "waiting": await client.scard(self.QUEUE_WAITING),
            }
        else:
            # 메모리 모드
            return {
                "pending": len(self._memory.queues["pending"]),
                "executing": len(self._memory.queues["executing"]),
                "waiting": len(self._memory.queues["waiting"]),
            }

    # ═══════════════════════════════════════════════════════════════
    # Loop Count Operations
    # ═══════════════════════════════════════════════════════════════

    async def increment_loop_count(self, session_id: str, role: str) -> int:
        """분기 루프 카운트 증가"""
        client = await self._get_client()

        if client:
            key = f"{self.CHAIN_KEY}:{session_id}"
            loop_counts_raw = await client.hget(key, "loop_counts")
            loop_counts = json.loads(loop_counts_raw) if loop_counts_raw else {}
            loop_counts[role] = loop_counts.get(role, 0) + 1
            await client.hset(key, "loop_counts", json.dumps(loop_counts))
            return loop_counts[role]
        else:
            # 메모리 모드
            chain = self._memory.chains.get(session_id, {})
            loop_counts_raw = chain.get("loop_counts", "{}")
            try:
                loop_counts = json.loads(loop_counts_raw) if isinstance(loop_counts_raw, str) else loop_counts_raw
            except (json.JSONDecodeError, TypeError):
                loop_counts = {}
            loop_counts[role] = loop_counts.get(role, 0) + 1
            chain["loop_counts"] = json.dumps(loop_counts)
            return loop_counts[role]

    async def get_loop_count(self, session_id: str, role: str) -> int:
        """분기 루프 카운트 조회"""
        client = await self._get_client()

        if client:
            key = f"{self.CHAIN_KEY}:{session_id}"
            loop_counts_raw = await client.hget(key, "loop_counts")
            if not loop_counts_raw:
                return 0
            loop_counts = json.loads(loop_counts_raw)
            return loop_counts.get(role, 0)
        else:
            # 메모리 모드
            chain = self._memory.chains.get(session_id, {})
            loop_counts_raw = chain.get("loop_counts", "{}")
            try:
                loop_counts = json.loads(loop_counts_raw) if isinstance(loop_counts_raw, str) else loop_counts_raw
            except (json.JSONDecodeError, TypeError):
                loop_counts = {}
            return loop_counts.get(role, 0)

    # ═══════════════════════════════════════════════════════════════
    # Active Sessions
    # ═══════════════════════════════════════════════════════════════

    async def get_active_sessions(self) -> dict[str, dict[str, Any]]:
        """활성 세션 (executing + waiting) 조회"""
        executing = await self.get_queue_sessions("executing")
        waiting = await self.get_queue_sessions("waiting")

        sessions = {}
        for session_id in executing + waiting:
            session = await self.get_session(session_id)
            if session:
                sessions[session_id] = session

        return sessions

    async def count_active_sessions(self) -> int:
        """활성 세션 수 조회"""
        counts = await self.get_queue_counts()
        return counts["executing"] + counts["waiting"]
