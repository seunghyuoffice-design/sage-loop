"""
Feedback Manager for 3-tier hierarchical feedback loop.

Redis 장애 시 메모리 폴백 지원.
"""

import fnmatch
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List, Iterator


class FeedbackLevel(str, Enum):
    """Feedback hierarchical levels matching Dyarchy bureaucracy."""

    MINISTRY = "ministry"  # 판서 → 실무자 (lowest tier)
    COUNCILOR = "councilor"  # 의정 → 판서 (middle tier)
    SAGE = "sage"  # 영의정 → 의정 (highest tier)


@dataclass
class Feedback:
    """Represents a single feedback item in the loop."""

    level: FeedbackLevel
    from_role: str  # Role providing feedback (judge)
    to_role: str  # Role receiving feedback (worker)
    reason: str  # Reason for feedback (issue description)
    action: str  # Required action (retry, escalate, find_alternative)
    max_retry: int  # Maximum retry attempts allowed
    current_retry: int = 0  # Current retry count
    session_id: str = ""  # Associated Sage session ID
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class _FallbackRedis:
    """In-memory Redis-like adapter for tests and fallback."""

    def __init__(self, store: dict[str, dict]):
        self._store = store

    def ping(self) -> bool:
        return True

    def hset(self, key: str, mapping: dict[str, str]) -> None:
        self._store[key] = dict(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._store.get(key, {}))

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def delete(self, key: str) -> int:
        existed = key in self._store
        self._store.pop(key, None)
        return 1 if existed else 0

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def scan_iter(self, match: str | None = None) -> Iterator[str]:
        for key in list(self._store.keys()):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    def hincrby(self, key: str, field: str, amount: int) -> int:
        data = self._store.setdefault(key, {})
        current = int(data.get(field, 0))
        new_value = current + amount
        data[field] = str(new_value)
        return new_value


class FeedbackManager:
    """Manages feedback storage and retrieval using Redis with memory fallback."""

    def __init__(self, redis_url: str | None = None):
        """Initialize with optional Redis URL (uses config if None).

        Args:
            redis_url: Redis connection URL (optional)
        """
        if redis_url is None:
            try:
                from ..config import get_hook_config

                config = get_hook_config()
                redis_url = config.redis_url
            except ImportError:
                redis_url = "redis://100.83.215.100:6380/0"

        self._redis_url = redis_url
        self._redis: Any = None
        self._fallback_store: dict[str, dict] = {}  # 메모리 폴백
        self._fallback_redis = _FallbackRedis(self._fallback_store)
        self._use_fallback = False

        self._connect()

    def _connect(self) -> None:
        """Redis 연결 (재시도 로직 포함)"""
        try:
            import redis

            self._redis = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            self._redis.ping()
            self._use_fallback = False
        except ImportError:
            print(
                "[FeedbackManager] Redis module not installed, using fallback",
                file=sys.stderr,
            )
            self._use_fallback = True
            self._redis = None
        except Exception as e:
            print(f"[FeedbackManager] Redis failed, using fallback: {e}", file=sys.stderr)
            self._use_fallback = True
            self._redis = None

    @property
    def redis(self) -> Any:
        """Redis client or in-memory fallback (tests용)."""
        if self._redis is not None:
            return self._redis
        return self._fallback_redis

    def _ensure_connection(self) -> bool:
        """Redis 연결 확인 및 재연결 시도

        Returns:
            True: Redis 사용 가능
            False: 폴백 사용
        """
        if self._use_fallback:
            # 재연결 시도
            self._connect()

        if self._redis is not None:
            try:
                self._redis.ping()
                return True
            except Exception:
                self._use_fallback = True
                return False

        return False

    def add_feedback(self, feedback: Feedback) -> None:
        """Add new feedback to queue (with fallback support).

        Args:
            feedback: Feedback object to add
        """
        key = f"feedback:{feedback.session_id}:{feedback.to_role}"
        data = {
            "level": feedback.level.value,
            "from": feedback.from_role,
            "to": feedback.to_role,
            "reason": feedback.reason,
            "action": feedback.action,
            "max_retry": str(feedback.max_retry),
            "current_retry": str(feedback.current_retry),
            "timestamp": feedback.timestamp,
        }

        if self._ensure_connection():
            self._redis.hset(key, mapping=data)
            self._redis.expire(key, 3600)
        else:
            # 메모리 폴백
            self._fallback_store[key] = data

    def get_pending(self, session_id: str) -> List[Feedback]:
        """Retrieve all pending feedbacks for a session (with fallback support).

        Args:
            session_id: Sage session ID

        Returns:
            List of pending Feedback objects
        """
        pattern = f"feedback:{session_id}:*"
        feedbacks = []

        if self._ensure_connection():
            # Redis 사용
            for key in self._redis.scan_iter(match=pattern):
                data = self._redis.hgetall(key)
                if data:
                    feedbacks.append(self._data_to_feedback(data, session_id))
        else:
            # 메모리 폴백
            for key, data in self._fallback_store.items():
                if fnmatch.fnmatch(key, pattern):
                    feedbacks.append(self._data_to_feedback(data, session_id))

        return feedbacks

    def _data_to_feedback(self, data: dict, session_id: str) -> Feedback:
        """Convert dict data to Feedback object.

        Args:
            data: Dictionary from Redis or fallback store
            session_id: Session ID

        Returns:
            Feedback object
        """
        return Feedback(
            level=FeedbackLevel(data["level"]),
            from_role=data["from"],
            to_role=data["to"],
            reason=data["reason"],
            action=data["action"],
            max_retry=int(data["max_retry"]),
            current_retry=int(data["current_retry"]),
            session_id=session_id,
            timestamp=data.get("timestamp", ""),
        )

    def increment_retry(self, session_id: str, to_role: str) -> int:
        """Increment retry counter for a feedback.

        Args:
            session_id: Sage session ID
            to_role: Target role receiving feedback

        Returns:
            New retry count
        """
        key = f"feedback:{session_id}:{to_role}"

        if self._ensure_connection():
            return self._redis.hincrby(key, "current_retry", 1)
        else:
            # 메모리 폴백
            if key in self._fallback_store:
                current = int(self._fallback_store[key].get("current_retry", 0))
                self._fallback_store[key]["current_retry"] = str(current + 1)
                return current + 1
            return 0

    def remove_feedback(self, session_id: str, to_role: str) -> None:
        """Remove feedback after successful completion.

        Args:
            session_id: Sage session ID
            to_role: Target role that completed the task
        """
        key = f"feedback:{session_id}:{to_role}"

        if self._ensure_connection():
            self._redis.delete(key)
        else:
            # 메모리 폴백
            self._fallback_store.pop(key, None)

    def get_feedback_count(self, session_id: str) -> int:
        """Get count of pending feedbacks for a session.

        Args:
            session_id: Sage session ID

        Returns:
            Number of pending feedbacks
        """
        pattern = f"feedback:{session_id}:*"

        if self._ensure_connection():
            count = 0
            for _ in self._redis.scan_iter(match=pattern):
                count += 1
            return count
        else:
            # 메모리 폴백
            count = 0
            for key in self._fallback_store:
                if fnmatch.fnmatch(key, pattern):
                    count += 1
            return count

    def get_by_level(self, session_id: str, level: FeedbackLevel) -> List[Feedback]:
        """Get feedbacks filtered by hierarchical level.

        Args:
            session_id: Sage session ID
            level: Feedback level to filter

        Returns:
            List of Feedback objects at specified level
        """
        all_feedbacks = self.get_pending(session_id)
        return [fb for fb in all_feedbacks if fb.level == level]

    def is_using_fallback(self) -> bool:
        """Check if currently using memory fallback.

        Returns:
            True if using fallback, False if using Redis
        """
        return self._use_fallback

    def clear_fallback_store(self) -> None:
        """Clear memory fallback store (for testing)."""
        self._fallback_store.clear()
