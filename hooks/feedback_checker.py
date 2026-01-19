#!/usr/bin/env python3
"""
Feedback Checker - 대기 중인 피드백 확인

분기 역할이나 사용자 승인이 필요한 경우 감지
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


def count_pending_feedback():
    """대기 중인 피드백 수 반환"""
    state = load_state()

    pending = 0

    # 분기 대기
    if state.get("pending_branch"):
        pending += 1

    # 사용자 승인 대기
    if state.get("waiting_approval"):
        pending += 1

    # 오류 복구 대기
    if state.get("pending_error_recovery"):
        pending += 1

    # 재시도 대기
    if state.get("retry_pending"):
        pending += 1

    return pending


def get_pending_details():
    """대기 중인 피드백 상세 정보"""
    state = load_state()

    details = []

    if state.get("pending_branch"):
        details.append({
            "type": "branch",
            "from_role": state.get("current_role"),
            "to_role": state.get("pending_branch"),
        })

    if state.get("waiting_approval"):
        details.append({
            "type": "approval",
            "role": state.get("current_role"),
            "reason": state.get("approval_reason", ""),
        })

    if state.get("pending_error_recovery"):
        details.append({
            "type": "error_recovery",
            "error": state.get("last_error", ""),
        })

    return details


def main():
    """메인: 대기 중인 피드백 수 출력"""
    count = count_pending_feedback()
    print(count)


if __name__ == "__main__":
    main()
