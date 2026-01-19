#!/usr/bin/env python3
"""
Completion Detector - Sage 체인 완료 신호 감지

모든 역할이 완료되었는지 확인하고 EXIT_SIGNAL 반환
Stop hook에서 호출됨
"""

import json
import os
import sys
from pathlib import Path

# 상태 파일 경로
STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
SESSION_ID = os.environ.get("SAGE_SESSION_ID", "")


def get_state_file():
    """세션별 상태 파일 경로"""
    if SESSION_ID:
        return STATE_DIR / f"sage_session_{SESSION_ID}.json"
    state_files = list(STATE_DIR.glob("sage_session_*.json"))
    if state_files:
        return max(state_files, key=lambda f: f.stat().st_mtime)
    return None


def load_state():
    """상태 파일 로드"""
    state_file = get_state_file()
    if state_file and state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def is_chain_complete():
    """체인이 완료되었는지 확인"""
    state = load_state()

    # 명시적 완료 신호
    if state.get("exit_signal", False):
        return True

    # 체인 역할 모두 완료 확인
    chain_roles = state.get("chain_roles", [])
    completed_roles = set(state.get("completed_roles", []))

    if not chain_roles:
        # 체인이 정의되지 않았으면 완료로 간주
        return True

    # 모든 역할 완료 확인
    all_complete = all(role in completed_roles for role in chain_roles)

    return all_complete


def get_exit_reason():
    """종료 이유 반환"""
    state = load_state()

    if state.get("exit_signal"):
        return state.get("exit_reason", "체인 완료")

    if state.get("error"):
        return f"오류: {state['error']}"

    chain_roles = state.get("chain_roles", [])
    completed_roles = state.get("completed_roles", [])

    if not chain_roles:
        return "체인 미정의"

    if len(completed_roles) >= len(chain_roles):
        return f"모든 역할 완료 ({len(completed_roles)}/{len(chain_roles)})"

    return None


def main():
    """메인: 완료 여부 출력 (true/false)"""
    if is_chain_complete():
        print("true")
    else:
        print("false")


if __name__ == "__main__":
    main()
