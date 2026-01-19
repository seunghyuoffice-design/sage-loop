"""
Session Management for Sage Feedback Loop

세션 ID 생성, 조회, 정리 기능 제공.
동시 실행 시 세션 격리를 위해 고유 ID 사용.
"""

import os
import time
import uuid

from .config import get_hook_config


def generate_session_id() -> str:
    """UUID4 기반 8자리 세션 ID 생성"""
    return uuid.uuid4().hex[:8]


def get_session_id() -> str:
    """현재 세션 ID 조회 (없으면 생성)

    우선순위:
    1. 환경변수 SAGE_SESSION_ID
    2. 기존 세션 파일에서 조회
    3. 새로 생성

    Returns:
        8자리 세션 ID
    """
    # 1. 환경변수 확인
    env_session = os.environ.get("SAGE_SESSION_ID")
    if env_session:
        return env_session

    # 2. 기존 세션 파일 확인 (가장 최근 것)
    config = get_hook_config()
    session_files = list(config.state_dir.glob("sage_loop_state_*.json"))
    if session_files:
        # 가장 최근 파일에서 세션 ID 추출
        latest = max(session_files, key=lambda f: f.stat().st_mtime)
        session_id = latest.stem.replace("sage_loop_state_", "")
        if session_id and len(session_id) == 8:
            return session_id

    # 3. 새로 생성
    new_id = generate_session_id()
    os.environ["SAGE_SESSION_ID"] = new_id
    return new_id


def cleanup_session(session_id: str) -> None:
    """세션 관련 파일 정리

    Args:
        session_id: 정리할 세션 ID
    """
    config = get_hook_config()

    patterns = [
        f"sage_loop_state_{session_id}.json",
        f"sage_circuit_breaker_{session_id}.json",
        f"sage_errors_{session_id}.log",
    ]

    for pattern in patterns:
        file_path = config.state_dir / pattern
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass  # 파일 삭제 실패 시 무시


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """오래된 세션 파일 삭제

    Args:
        max_age_hours: 삭제 기준 시간 (기본: 24시간)

    Returns:
        삭제된 파일 수
    """
    config = get_hook_config()
    cutoff_time = time.time() - (max_age_hours * 3600)
    deleted_count = 0

    # 모든 Sage 관련 임시 파일 검색
    patterns = [
        "sage_loop_state_*.json",
        "sage_circuit_breaker_*.json",
        "sage_errors_*.log",
    ]

    for pattern in patterns:
        for file_path in config.state_dir.glob(pattern):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            except OSError:
                pass  # 파일 접근/삭제 실패 시 무시

    return deleted_count


def get_session_info(session_id: str | None = None) -> dict:
    """세션 정보 조회

    Args:
        session_id: 조회할 세션 ID (None이면 현재 세션)

    Returns:
        세션 정보 딕셔너리
    """
    sid = session_id or get_session_id()

    from .config import (
        get_circuit_breaker_path,
        get_error_log_path,
        get_state_file_path,
    )

    state_file = get_state_file_path(sid)
    cb_file = get_circuit_breaker_path(sid)
    log_file = get_error_log_path(sid)

    return {
        "session_id": sid,
        "state_file": str(state_file),
        "state_exists": state_file.exists(),
        "circuit_breaker_file": str(cb_file),
        "circuit_breaker_exists": cb_file.exists(),
        "error_log_file": str(log_file),
        "error_log_exists": log_file.exists(),
    }
