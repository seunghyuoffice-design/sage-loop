#!/usr/bin/env python3
"""
Circuit Breaker - 무한 루프 방지 안전장치

연속 오류나 과도한 루프 감지 시 체인 중단
Stop hook에서 호출됨
"""

import json
import os
import sys
import time
from pathlib import Path

# 상태 파일 경로
STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
SESSION_ID = os.environ.get("SAGE_SESSION_ID", "")

# Circuit breaker 설정
MAX_CONSECUTIVE_ERRORS = int(os.environ.get("SAGE_MAX_ERRORS", "3"))
MAX_LOOPS_PER_ROLE = int(os.environ.get("SAGE_MAX_ROLE_LOOPS", "5"))
COOLDOWN_SECONDS = int(os.environ.get("SAGE_COOLDOWN", "60"))


def get_breaker_file():
    """Circuit breaker 상태 파일"""
    if SESSION_ID:
        return STATE_DIR / f"sage_circuit_breaker_{SESSION_ID}.json"
    return STATE_DIR / "sage_circuit_breaker.json"


def load_breaker_state():
    """Breaker 상태 로드"""
    breaker_file = get_breaker_file()
    if breaker_file.exists():
        try:
            return json.loads(breaker_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "consecutive_errors": 0,
        "role_loop_counts": {},
        "last_error_time": None,
        "tripped": False,
        "trip_reason": None,
    }


def save_breaker_state(state):
    """Breaker 상태 저장"""
    breaker_file = get_breaker_file()
    breaker_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def record_error(error_msg=""):
    """오류 기록"""
    state = load_breaker_state()
    state["consecutive_errors"] += 1
    state["last_error_time"] = time.time()
    state["last_error"] = error_msg

    if state["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS:
        state["tripped"] = True
        state["trip_reason"] = f"연속 오류 {state['consecutive_errors']}회"

    save_breaker_state(state)


def record_role_loop(role):
    """역할 루프 기록"""
    state = load_breaker_state()
    counts = state.get("role_loop_counts", {})
    counts[role] = counts.get(role, 0) + 1
    state["role_loop_counts"] = counts

    if counts[role] >= MAX_LOOPS_PER_ROLE:
        state["tripped"] = True
        state["trip_reason"] = f"역할 '{role}' 루프 {counts[role]}회"

    save_breaker_state(state)


def record_success():
    """성공 기록 (오류 카운터 리셋)"""
    state = load_breaker_state()
    state["consecutive_errors"] = 0
    state["last_error"] = None
    save_breaker_state(state)


def is_circuit_open():
    """Circuit이 열려있는지 (중단 필요) 확인"""
    state = load_breaker_state()

    # 이미 트립됨
    if state.get("tripped"):
        return True

    # 쿨다운 중인지 확인
    last_error_time = state.get("last_error_time")
    if last_error_time:
        elapsed = time.time() - last_error_time
        if elapsed < COOLDOWN_SECONDS and state.get("consecutive_errors", 0) >= 2:
            return True

    return False


def reset_breaker():
    """Circuit breaker 리셋"""
    breaker_file = get_breaker_file()
    if breaker_file.exists():
        breaker_file.unlink()


def get_status():
    """상태 정보 반환"""
    state = load_breaker_state()
    return {
        "tripped": state.get("tripped", False),
        "trip_reason": state.get("trip_reason"),
        "consecutive_errors": state.get("consecutive_errors", 0),
        "role_loop_counts": state.get("role_loop_counts", {}),
    }


def main():
    """메인: circuit이 닫혀있으면 exit 0, 열려있으면 exit 1"""
    if is_circuit_open():
        status = get_status()
        print(f"Circuit OPEN: {status.get('trip_reason', 'Unknown')}", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
