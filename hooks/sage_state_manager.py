#!/usr/bin/env python3
"""
Sage State Manager - 세션 상태 관리

sage 체인 실행 중 상태 추적 및 관리
stop-hook.sh와 다른 hook에서 호출됨
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 상태 파일 경로
STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
PROJECT_ROOT = Path(os.environ.get("SAGE_PROJECT_ROOT", "/home/rovers/Dyarchy-v3"))

# 체인 정의 (config.yaml에서 로드 가능)
CHAINS = {
    "FULL": [
        "ideator", "analyst", "critic", "censor", "academy",
        "architect", "left-state-councilor", "right-state-councilor",
        "executor", "inspector", "validator", "historian",
        "reflector", "improver"
    ],
    "QUICK": ["critic", "architect", "executor", "validator", "historian"],
    "REVIEW": ["critic", "validator"],
    "DESIGN": ["ideator", "analyst", "critic", "architect"],
}


def get_session_id():
    """세션 ID 획득 또는 생성"""
    session_id = os.environ.get("SAGE_SESSION_ID")
    if session_id:
        return session_id

    # 새 세션 ID 생성
    import hashlib
    ts = str(time.time()).encode()
    return hashlib.md5(ts).hexdigest()[:8]


def get_state_file(session_id=None):
    """상태 파일 경로"""
    sid = session_id or get_session_id()
    return STATE_DIR / f"sage_session_{sid}.json"


def load_state(session_id=None):
    """상태 로드"""
    state_file = get_state_file(session_id)
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_state(state, session_id=None):
    """상태 저장"""
    state_file = get_state_file(session_id)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def init_session(task: str, chain_type: str = "FULL"):
    """새 세션 초기화"""
    session_id = get_session_id()

    chain_roles = CHAINS.get(chain_type, CHAINS["FULL"])

    state = {
        "session_id": session_id,
        "task": task,
        "chain_type": chain_type,
        "chain_roles": chain_roles,
        "current_role": None,
        "completed_roles": [],
        "role_outputs": {},
        "active": True,
        "exit_signal": False,
        "started_at": datetime.now().isoformat(),
        "loop_count": 0,
    }

    save_state(state, session_id)
    return state


def start_role(role: str, session_id=None):
    """역할 시작"""
    state = load_state(session_id)
    state["current_role"] = role
    state["loop_count"] = state.get("loop_count", 0) + 1
    save_state(state, session_id)
    return state


def complete_role(role: str, output: dict = None, session_id=None):
    """역할 완료"""
    state = load_state(session_id)

    if role not in state.get("completed_roles", []):
        state.setdefault("completed_roles", []).append(role)

    if output:
        state.setdefault("role_outputs", {})[role] = output

    # 다음 역할 확인
    chain_roles = state.get("chain_roles", [])
    completed = set(state.get("completed_roles", []))

    next_role = None
    for r in chain_roles:
        if r not in completed:
            next_role = r
            break

    state["current_role"] = next_role

    # 모든 역할 완료 시 exit_signal 설정
    if next_role is None:
        state["exit_signal"] = True
        state["exit_reason"] = "모든 역할 완료"
        state["completed_at"] = datetime.now().isoformat()

    save_state(state, session_id)
    return state


def get_next_role(session_id=None):
    """다음 역할 반환"""
    state = load_state(session_id)
    chain_roles = state.get("chain_roles", [])
    completed = set(state.get("completed_roles", []))

    for role in chain_roles:
        if role not in completed:
            return role
    return None


def set_exit_signal(reason: str = "완료", session_id=None):
    """종료 신호 설정"""
    state = load_state(session_id)
    state["exit_signal"] = True
    state["exit_reason"] = reason
    state["active"] = False
    save_state(state, session_id)
    return state


def get_progress(session_id=None):
    """진행 상황 반환"""
    state = load_state(session_id)
    chain_roles = state.get("chain_roles", [])
    completed = state.get("completed_roles", [])

    return {
        "session_id": state.get("session_id"),
        "chain_type": state.get("chain_type"),
        "total_roles": len(chain_roles),
        "completed_roles": len(completed),
        "current_role": state.get("current_role"),
        "next_role": get_next_role(session_id),
        "progress_pct": round(len(completed) / max(len(chain_roles), 1) * 100),
        "active": state.get("active", False),
        "exit_signal": state.get("exit_signal", False),
    }


def cleanup_session(session_id=None):
    """세션 정리"""
    state_file = get_state_file(session_id)
    if state_file.exists():
        state_file.unlink()

    # circuit breaker도 정리
    breaker_file = STATE_DIR / f"sage_circuit_breaker_{session_id or get_session_id()}.json"
    if breaker_file.exists():
        breaker_file.unlink()


def main():
    parser = argparse.ArgumentParser(description="Sage State Manager")
    parser.add_argument("--session", "-s", help="세션 ID (환경변수 대신 직접 지정)")
    subparsers = parser.add_subparsers(dest="command", help="명령")

    # init
    init_parser = subparsers.add_parser("init", help="세션 초기화")
    init_parser.add_argument("task", help="작업 설명")
    init_parser.add_argument("--chain", default="FULL", help="체인 타입")

    # start
    start_parser = subparsers.add_parser("start", help="역할 시작")
    start_parser.add_argument("role", help="역할 이름")

    # complete
    complete_parser = subparsers.add_parser("complete", help="역할 완료")
    complete_parser.add_argument("role", help="역할 이름")
    complete_parser.add_argument("--output", help="출력 JSON")

    # next
    subparsers.add_parser("next", help="다음 역할")

    # progress
    subparsers.add_parser("progress", help="진행 상황")

    # exit
    exit_parser = subparsers.add_parser("exit", help="종료 신호")
    exit_parser.add_argument("--reason", default="완료", help="종료 이유")

    # cleanup
    subparsers.add_parser("cleanup", help="세션 정리")

    args = parser.parse_args()

    # --session 인자가 있으면 환경변수로 설정 (모든 함수에서 사용)
    if args.session:
        os.environ["SAGE_SESSION_ID"] = args.session

    if args.command == "init":
        state = init_session(args.task, args.chain)
        print(json.dumps(state, ensure_ascii=False))

    elif args.command == "start":
        state = start_role(args.role)
        print(json.dumps({"started": args.role, "loop": state.get("loop_count", 0)}))

    elif args.command == "complete":
        output = json.loads(args.output) if args.output else None
        state = complete_role(args.role, output)
        # state에서 세션 ID를 가져와서 next_role 호출
        session_id = state.get("session_id")
        next_role = get_next_role(session_id)
        if next_role:
            print(f"NEXT: {next_role}")
        else:
            print("APPROVE")

    elif args.command == "next":
        next_role = get_next_role()
        if next_role:
            print(next_role)
        else:
            print("")

    elif args.command == "progress":
        progress = get_progress()
        print(json.dumps(progress, ensure_ascii=False))

    elif args.command == "exit":
        state = set_exit_signal(args.reason)
        print(json.dumps({"exit_signal": True, "reason": args.reason}))

    elif args.command == "cleanup":
        cleanup_session()
        print("cleaned")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
