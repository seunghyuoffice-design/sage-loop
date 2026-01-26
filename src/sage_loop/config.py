"""
Sage Configuration - Feedback Loop Pattern

환경 변수:
    SAGE_API_PORT: API 포트 (기본: 8020)
    SAGE_REDIS_HOST: Redis 호스트 (기본: redis)
    SAGE_REDIS_PORT: Redis 포트 (기본: 6380, Sage 전용)
    SAGE_MODE: 실행 모드 (full-auto, plan-first, interactive)
    SAGE_CONFIG_PATH: 체인 설정 YAML 경로
    SAGE_MONITOR_INTERVAL: 감독 루프 간격 (초)
    SAGE_STALL_THRESHOLD: 정체 감지 임계값 (초)

Hook 환경 변수 (Phase A 추가):
    SAGE_STATE_DIR: 상태 파일 디렉토리 (기본: /tmp)
    SAGE_PROJECT_ROOT: 프로젝트 루트 (기본: ~/Dyarchy-v3)
    SAGE_MAX_LOOPS: 최대 루프 횟수 (기본: 50)
    SAGE_SESSION_TIMEOUT: 세션 타임아웃 초 (기본: 3600)
    SAGE_STAGNATION_THRESHOLD: 정체 감지 임계값 (기본: 3)
    SAGE_DEBUG: 디버그 모드 (기본: 0)

포트:
    Sage: 6380 (오케스트레이터 상태)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    """Redis 연결 설정 (Sage 전용 포트 6380)"""

    host: str = "localhost"  # 로컬 개발용, Docker에서는 환경변수로 "redis" 설정
    port: int = 6380  # Sage 전용
    db: int = 0
    password: Optional[str] = None

    model_config = {"env_prefix": "SAGE_REDIS_"}


class SupervisorConfig(BaseSettings):
    """감독 루프 설정"""

    monitor_interval: float = 5.0  # 5초
    stall_threshold: int = 300  # 5분
    max_subscribers: int = 100

    model_config = {"env_prefix": "SAGE_SUPERVISOR_"}


class ChainConfig(BaseSettings):
    """체인 실행 설정"""

    max_total_branches: int = 5
    timeout_minutes: int = 60
    auto_confirm: bool = False

    model_config = {"env_prefix": "SAGE_CHAIN_"}


class SageSettings(BaseSettings):
    """Sage 통합 설정"""

    # 기본 설정
    api_port: int = 8020
    mode: str = "plan-first"  # full-auto, plan-first, interactive
    config_path: str = "/app/skills/sage/config.yaml"

    # 하위 설정
    redis: RedisConfig = Field(default_factory=RedisConfig)
    supervisor: SupervisorConfig = Field(default_factory=SupervisorConfig)
    chain: ChainConfig = Field(default_factory=ChainConfig)

    model_config = {"env_prefix": "SAGE_"}

    def get_config_path(self) -> Path:
        """설정 파일 경로 반환 (fallback 포함)"""
        path = Path(self.config_path)
        if path.exists():
            return path

        # 로컬 개발용 fallback
        local_path = Path(__file__).parent.parent.parent / ".claude" / "skills" / "sage" / "config.yaml"
        if local_path.exists():
            return local_path

        raise FileNotFoundError(f"Sage config not found: {self.config_path}")


_settings: SageSettings | None = None


def get_settings() -> SageSettings:
    """싱글턴 설정 반환"""
    global _settings
    if _settings is None:
        _settings = SageSettings()
    return _settings


def reset_settings() -> None:
    """설정 리셋 (테스트용)"""
    global _settings
    _settings = None


# ============================================================================
# Hook Configuration (Phase A: 기반 인프라)
# ============================================================================


@dataclass(frozen=True)
class HookConfig:
    """Hook용 설정 (환경변수 기반, 불변)"""

    state_dir: Path
    project_root: Path
    redis_host: str
    redis_port: int
    redis_db: int
    max_loops: int
    session_timeout: int
    stagnation_threshold: int
    debug: bool

    @property
    def redis_url(self) -> str:
        """Redis URL 생성"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


_hook_config: HookConfig | None = None


def get_hook_config() -> HookConfig:
    """Hook 설정 싱글턴 반환 (환경변수에서 로드)"""
    global _hook_config
    if _hook_config is None:
        _hook_config = HookConfig(
            state_dir=Path(os.environ.get("SAGE_STATE_DIR", "/tmp")),
            project_root=Path(os.environ.get("SAGE_PROJECT_ROOT", str(Path.home() / "Dyarchy-v3"))),
            redis_host=os.environ.get("SAGE_REDIS_HOST", "localhost"),
            redis_port=int(os.environ.get("SAGE_REDIS_PORT", "6380")),
            redis_db=int(os.environ.get("SAGE_REDIS_DB", "0")),
            max_loops=int(os.environ.get("SAGE_MAX_LOOPS", "50")),
            session_timeout=int(os.environ.get("SAGE_SESSION_TIMEOUT", "3600")),
            stagnation_threshold=int(os.environ.get("SAGE_STAGNATION_THRESHOLD", "3")),
            debug=os.environ.get("SAGE_DEBUG", "0") == "1",
        )
    return _hook_config


def reset_hook_config() -> None:
    """Hook 설정 리셋 (테스트용)"""
    global _hook_config
    _hook_config = None


# ============================================================================
# Path Helpers (세션 ID 기반 파일 경로)
# ============================================================================


def get_state_file_path(session_id: str) -> Path:
    """상태 파일 경로 반환"""
    config = get_hook_config()
    return config.state_dir / f"sage_loop_state_{session_id}.json"


def get_circuit_breaker_path(session_id: str) -> Path:
    """Circuit breaker 상태 파일 경로 반환"""
    config = get_hook_config()
    return config.state_dir / f"sage_circuit_breaker_{session_id}.json"


def get_error_log_path(session_id: str) -> Path:
    """에러 로그 파일 경로 반환"""
    config = get_hook_config()
    return config.state_dir / f"sage_errors_{session_id}.log"
