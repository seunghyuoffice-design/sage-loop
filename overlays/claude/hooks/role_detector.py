#!/usr/bin/env python3
"""
Role Detector - 현재 활성 역할 감지

Stop hook과 다른 hook에서 현재 역할을 확인하기 위해 사용
상태 파일에서 현재 역할을 읽음
"""

import argparse
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
    # 세션 ID 없으면 가장 최근 상태 파일 찾기
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


def get_current_role():
    """현재 활성 역할 반환"""
    state = load_state()
    return state.get("current_role", "")


def is_sage_active():
    """sage 루프가 활성 상태인지 확인"""
    state = load_state()
    return state.get("active", False) and state.get("chain_type") is not None


def get_next_role():
    """다음 실행할 역할 반환"""
    state = load_state()
    chain_roles = state.get("chain_roles", [])
    completed = set(state.get("completed_roles", []))

    for role in chain_roles:
        if role not in completed:
            return role
    return None


def get_chain_progress():
    """체인 진행 상황 반환"""
    state = load_state()
    chain_roles = state.get("chain_roles", [])
    completed = state.get("completed_roles", [])
    current = state.get("current_role", "")

    return {
        "total": len(chain_roles),
        "completed": len(completed),
        "current": current,
        "remaining": len(chain_roles) - len(completed),
        "chain_type": state.get("chain_type", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Role Detector")
    parser.add_argument("--current", action="store_true", help="현재 역할 출력")
    parser.add_argument("--next", action="store_true", help="다음 역할 출력")
    parser.add_argument("--active", action="store_true", help="sage 활성 여부")
    parser.add_argument("--progress", action="store_true", help="진행 상황 JSON")
    parser.add_argument("--json", action="store_true", help="JSON 형식 출력")

    args = parser.parse_args()

    if args.current:
        role = get_current_role()
        if args.json:
            print(json.dumps({"current_role": role}))
        else:
            print(role)

    elif args.next:
        role = get_next_role()
        if args.json:
            print(json.dumps({"next_role": role}))
        else:
            print(role or "")

    elif args.active:
        active = is_sage_active()
        if args.json:
            print(json.dumps({"active": active}))
        else:
            print("true" if active else "false")

    elif args.progress:
        progress = get_chain_progress()
        print(json.dumps(progress, ensure_ascii=False))

    else:
        # 기본: 현재 역할
        print(get_current_role())


if __name__ == "__main__":
    main()
