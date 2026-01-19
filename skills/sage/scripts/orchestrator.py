#!/usr/bin/env python3
"""
Sage Orchestrator - 체인 오케스트레이션 엔진

컨텍스트 최소화를 위해 모든 로직은 Python에서 처리
Claude는 출력만 읽고 행동

v2: stop-hook.sh 호환 상태 파일 형식 사용
"""

import argparse
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# 상태 파일 경로 (stop-hook.sh 호환)
STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def get_session_id() -> str:
    """세션 ID 획득 또는 생성"""
    session_id = os.environ.get("SAGE_SESSION_ID")
    if session_id:
        return session_id
    # 새 세션 ID 생성
    ts = str(time.time()).encode()
    new_id = f"orch-{hashlib.md5(ts).hexdigest()[:8]}"
    os.environ["SAGE_SESSION_ID"] = new_id
    return new_id


def get_state_file() -> Path:
    """세션별 상태 파일 경로 (stop-hook.sh 호환)"""
    session_id = get_session_id()
    return STATE_DIR / f"sage_session_{session_id}.json"


# 체인 정의 (config.yaml에서 로드)
def load_config() -> dict:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text()) or {}
    return {}


def load_state() -> dict:
    state_file = get_state_file()
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    # stop-hook.sh 호환 기본 상태
    return {
        "session_id": get_session_id(),
        "chain_type": None,
        "chain_roles": [],
        "current_role": None,
        "completed_roles": [],
        "role_outputs": {},
        "active": False,
        "exit_signal": False,
        "loop_count": 0,
    }


def save_state(state: dict):
    state_file = get_state_file()
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def clear_state():
    state_file = get_state_file()
    if state_file.exists():
        state_file.unlink()


# 체인 선택 로직
def select_chain(task: str, config: dict) -> str:
    task_lower = task.lower()
    chains = config.get("chains", {})

    for chain_name, chain_cfg in chains.items():
        triggers = chain_cfg.get("triggers", {})
        keywords = triggers.get("keywords", [])
        for kw in keywords:
            if kw.lower() in task_lower:
                return chain_name

    return config.get("defaults", {}).get("fallback_chain", "FULL")


# 다음 역할 결정 (stop-hook.sh 호환 필드명 사용)
def get_next_role(state: dict, config: dict) -> Optional[str]:
    # stop-hook.sh 호환: chain_type, chain_roles, completed_roles
    chain_name = state.get("chain_type") or state.get("chain")
    if not chain_name:
        return None

    # chain_roles가 이미 있으면 사용
    roles = state.get("chain_roles", [])

    # 없으면 config에서 조회
    if not roles:
        chains = config.get("chains", {})
        chain = chains.get(chain_name, {})
        roles = chain.get("roles", [])

    # stop-hook.sh 호환: completed_roles
    completed = set(state.get("completed_roles", state.get("completed", [])))

    for role in roles:
        if role not in completed:
            return role

    return None  # 모든 역할 완료


# 분기 체크
def check_branch(role: str, result: str, state: dict, config: dict) -> Optional[str]:
    chain_name = state.get("chain_type") or state.get("chain")
    if not chain_name:
        return None

    chains = config.get("chains", {})
    chain = chains.get(chain_name, {})
    branches = chain.get("branches", [])

    for branch in branches:
        if branch.get("from") == role:
            condition = branch.get("condition", "")
            # 결과에 조건 키워드가 있으면 분기
            if condition.lower() in result.lower():
                return branch.get("to")

    return None


def main():
    parser = argparse.ArgumentParser(description="Sage Orchestrator")
    parser.add_argument("task", nargs="?", help="작업 설명")
    parser.add_argument("--complete", metavar="ROLE", help="역할 완료 보고")
    parser.add_argument("--result", default="", help="역할 실행 결과 (분기 판단용)")
    parser.add_argument("--status", action="store_true", help="현재 상태 출력")
    parser.add_argument("--reset", action="store_true", help="상태 초기화")

    args = parser.parse_args()
    config = load_config()
    state = load_state()

    # 상태 초기화
    if args.reset:
        clear_state()
        print("RESET: OK")
        return

    # 상태 출력
    if args.status:
        chain_type = state.get("chain_type") or state.get("chain")
        if chain_type:
            completed = state.get("completed_roles", state.get("completed", []))
            print(f"CHAIN: {chain_type}")
            print(f"PHASE: {len(completed)}")
            print(f"COMPLETED: {', '.join(completed) or 'none'}")
            next_role = get_next_role(state, config)
            if next_role:
                print(f"NEXT: {next_role}")
            else:
                print("STATUS: all_complete")
        else:
            print("STATUS: idle")
        return

    # 역할 완료 처리
    if args.complete:
        role = args.complete

        # stop-hook.sh 호환: completed_roles
        completed_roles = state.get("completed_roles", state.get("completed", []))
        if role not in completed_roles:
            completed_roles.append(role)
            state["completed_roles"] = completed_roles
            state["completed"] = completed_roles  # 하위 호환

        # 분기 체크
        branch_to = check_branch(role, args.result, state, config)
        if branch_to:
            save_state(state)
            print(f"BRANCH: {branch_to}")
            return

        # 다음 역할 확인
        next_role = get_next_role(state, config)
        state["current_role"] = next_role
        save_state(state)

        if next_role:
            print(f"NEXT: {next_role}")
        else:
            print("APPROVE")
        return

    # 새 작업 시작
    if args.task:
        # 체인 선택
        chain = select_chain(args.task, config)

        # 체인 역할 목록 조회
        chains = config.get("chains", {})
        chain_def = chains.get(chain, {})
        roles = chain_def.get("roles", [])

        # stop-hook.sh 호환 상태 구조
        state = {
            "session_id": get_session_id(),
            "task": args.task,
            "chain_type": chain,
            "chain": chain,  # 하위 호환
            "chain_roles": roles,
            "current_role": None,
            "completed_roles": [],
            "completed": [],  # 하위 호환
            "role_outputs": {},
            "active": True,
            "exit_signal": False,
            "started_at": datetime.now().isoformat(),
            "loop_count": 0,
        }
        save_state(state)

        # 첫 번째 역할
        next_role = get_next_role(state, config)

        print(f"CHAIN: {chain}")
        if next_role:
            print(f"NEXT: {next_role}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
