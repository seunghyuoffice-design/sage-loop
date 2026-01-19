"""
Error Logger for Sage Feedback Loop

세션별 에러 로그 관리.
로그 로테이션 지원으로 디스크 공간 관리.
"""

import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from .config import get_error_log_path, get_hook_config
from .session import get_session_id

# 세션별 로거 캐시
_loggers: dict[str, logging.Logger] = {}


def get_logger(session_id: str | None = None) -> logging.Logger:
    """세션별 로거 반환 (로그 로테이션 지원)

    Args:
        session_id: 세션 ID (None이면 현재 세션)

    Returns:
        설정된 로거
    """
    sid = session_id or get_session_id()

    if sid in _loggers:
        return _loggers[sid]

    logger = logging.getLogger(f"sage_{sid}")
    logger.setLevel(logging.DEBUG)

    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()

    # 로그 로테이션 핸들러 추가 (1MB 제한, 5개 백업)
    log_path = get_error_log_path(sid)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,  # 1MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)

    # 포맷 설정
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    _loggers[sid] = logger
    return logger


def log_error(
    source: str,
    message: str,
    exception: Optional[Exception] = None,
    session_id: Optional[str] = None,
) -> None:
    """에러를 세션별 로그 파일에 기록

    Args:
        source: 에러 소스 (예: "circuit_breaker", "feedback_checker")
        message: 에러 메시지
        exception: 예외 객체 (선택)
        session_id: 세션 ID (선택)
    """
    logger = get_logger(session_id)

    log_message = f"[{source}] {message}"
    if exception:
        log_message += f" | Exception: {type(exception).__name__}: {exception}"

    logger.error(log_message)


def log_warning(
    source: str,
    message: str,
    session_id: Optional[str] = None,
) -> None:
    """경고를 세션별 로그 파일에 기록

    Args:
        source: 경고 소스
        message: 경고 메시지
        session_id: 세션 ID (선택)
    """
    logger = get_logger(session_id)
    logger.warning(f"[{source}] {message}")


def log_debug(
    source: str,
    message: str,
    session_id: Optional[str] = None,
) -> None:
    """디버그 로그 (SAGE_DEBUG=1일 때만 파일에 기록)

    Args:
        source: 디버그 소스
        message: 디버그 메시지
        session_id: 세션 ID (선택)
    """
    config = get_hook_config()
    if not config.debug:
        return

    logger = get_logger(session_id)
    logger.debug(f"[{source}] {message}")


def log_info(
    source: str,
    message: str,
    session_id: Optional[str] = None,
) -> None:
    """정보 로그 기록

    Args:
        source: 정보 소스
        message: 정보 메시지
        session_id: 세션 ID (선택)
    """
    logger = get_logger(session_id)
    logger.info(f"[{source}] {message}")


def get_recent_errors(
    session_id: Optional[str] = None,
    limit: int = 10,
) -> list[str]:
    """최근 에러 로그 조회

    Args:
        session_id: 세션 ID (선택)
        limit: 반환할 최대 라인 수

    Returns:
        최근 에러 로그 라인 리스트
    """
    sid = session_id or get_session_id()
    log_path = get_error_log_path(sid)

    if not log_path.exists():
        return []

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-limit:] if line.strip()]
    except OSError:
        return []


def clear_logger_cache() -> None:
    """로거 캐시 초기화 (테스트용)"""
    global _loggers
    for logger in _loggers.values():
        logger.handlers.clear()
    _loggers.clear()
