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
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# 상태 파일 경로 (stop-hook.sh 호환)
STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

# 역할별 설명 (TodoWrite용)
ROLE_DESCRIPTIONS = {
    "ideator": ("아이디어 생성", "아이디어 생성 중"),
    "analyst": ("분석/선별", "분석 중"),
    "critic": ("위험/결함 비판", "비판 검토 중"),
    "censor": ("RULES 사전 봉쇄", "규칙 검증 중"),
    "academy": ("학술 자문", "학술 자문 중"),
    "architect": ("설계 수립", "설계 중"),
    "left-state-councilor": ("내정 검토", "내정 검토 중"),
    "right-state-councilor": ("실무 검토", "실무 검토 중"),
    "sage": ("최종 승인", "최종 승인 중"),
    "executor": ("구현", "구현 중"),
    "inspector": ("감찰", "감찰 중"),
    "validator": ("검증", "검증 중"),
    "historian": ("기록", "기록 중"),
    "reflector": ("회고", "회고 중"),
    "improver": ("개선", "개선 중"),
    "feasibility-checker": ("실현 가능성 검증", "가능성 검증 중"),
    "constraint-enforcer": ("제약 조건 강제", "제약 검증 중"),
    "policy-keeper": ("정책 관리", "정책 검토 중"),
}


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


def generate_todos(roles: list) -> list:
    """체인 역할 목록으로 TodoWrite용 JSON 생성"""
    todos = []
    for i, role in enumerate(roles, 1):
        desc, active = ROLE_DESCRIPTIONS.get(role, (role, f"{role} 실행 중"))
        todos.append({
            "content": f"Phase {i}: {role} - {desc}",
            "status": "pending",
            "activeForm": active
        })
    return todos


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

        # 상태 검증: 활성 세션이 있어야 함
        chain_roles = state.get("chain_roles", [])
        if not chain_roles or not state.get("active", False):
            print("ERROR: 활성 세션 없음. 먼저 작업을 시작하세요.")
            sys.exit(1)

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

        # 다음 역할 확인 및 current_role 업데이트
        next_role = get_next_role(state, config)
        state["current_role"] = next_role

        # 모든 역할 완료 시 exit_signal 설정 (chain_roles 기준으로 검증)
        all_completed = len(completed_roles) >= len(chain_roles)
        if next_role is None and all_completed:
            state["exit_signal"] = True
            state["exit_reason"] = "모든 역할 완료"
            state["active"] = False

        save_state(state)

        if next_role:
            print(f"NEXT: {next_role}")
        elif all_completed:
            print("APPROVE")
        else:
            # 비정상: 다음 역할 없는데 완료도 아님
            print(f"ERROR: 상태 불일치. completed={len(completed_roles)}, total={len(chain_roles)}")
            sys.exit(1)
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

        # 출력
        print(f"CHAIN: {chain}")
        if next_role:
            print(f"NEXT: {next_role}")

        # TODO JSON 출력 (Claude가 TodoWrite 호출하도록 강제)
        todos = generate_todos(roles)
        print("TODO_REQUIRED:")
        print(json.dumps({"todos": todos}, ensure_ascii=False))
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
