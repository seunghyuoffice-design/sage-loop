#!/usr/bin/env python3
"""
Sage Orchestrator - 체인 오케스트레이션 엔진

컨텍스트 최소화를 위해 모든 로직은 Python에서 처리
Claude는 출력만 읽고 행동

v3: 인덱스 기반 역할 추적 + 분기 루프백 + Sage 거부 처리
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
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
CURRENT_SESSION_FILE = STATE_DIR / "sage_current_session"  # v3.2: 활성 세션 추적

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


def get_session_id(create_new: bool = False) -> str:
    """세션 ID 획득 또는 생성

    v3.2: 우선순위
    1. 환경 변수 SAGE_SESSION_ID
    2. 현재 세션 파일 (/tmp/sage_current_session)
    3. 새 ID 생성 (create_new=True일 때만)

    Args:
        create_new: True면 기존 세션 무시하고 새 ID 생성
    """
    # 1. 환경 변수 체크
    session_id = os.environ.get("SAGE_SESSION_ID")
    if session_id and not create_new:
        return session_id

    # 2. 현재 세션 파일 체크 (v3.2)
    if not create_new and CURRENT_SESSION_FILE.exists():
        try:
            stored_id = CURRENT_SESSION_FILE.read_text().strip()
            if stored_id:
                os.environ["SAGE_SESSION_ID"] = stored_id
                return stored_id
        except (IOError, OSError):
            pass

    # 3. 새 세션 ID 생성
    ts = str(time.time()).encode()
    new_id = f"orch-{hashlib.sha256(ts).hexdigest()[:8]}"
    os.environ["SAGE_SESSION_ID"] = new_id
    return new_id


def set_current_session(session_id: str) -> None:
    """현재 세션 ID를 파일에 저장 (v3.2)"""
    try:
        CURRENT_SESSION_FILE.write_text(session_id)
    except (IOError, OSError) as e:
        print(f"WARNING: 세션 파일 저장 실패: {e}", file=sys.stderr)


def clear_current_session() -> None:
    """현재 세션 파일 삭제 (v3.2)"""
    try:
        if CURRENT_SESSION_FILE.exists():
            CURRENT_SESSION_FILE.unlink()
    except (IOError, OSError):
        pass


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
    # v3 기본 상태
    default_state = {
        "session_id": get_session_id(),
        "chain_type": None,
        "chain_roles": [],
        "current_index": 0,  # v3: 인덱스 기반 추적
        "current_role": None,
        "completed_indices": [],  # v3: 완료된 인덱스 목록
        "completed_roles": [],  # 하위 호환
        "role_outputs": {},
        "active": False,
        "exit_signal": False,
        "loop_count": 0,
        # v3: 분기 상태
        "branch_active": None,  # 현재 활성 분기 역할
        "branch_return_index": None,  # 분기 완료 후 돌아갈 인덱스
        "branch_loops": {},  # {from_role: count} 분기 횟수 추적
    }

    state_file = get_state_file()
    if state_file.exists():
        try:
            loaded = json.loads(state_file.read_text())
            # 기본 상태와 병합 (기존 값 우선)
            default_state.update(loaded)
            return default_state
        except (json.JSONDecodeError, IOError):
            pass

    return default_state


def save_state(state: dict) -> None:
    state_file = get_state_file()
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def clear_state() -> None:
    state_file = get_state_file()
    if state_file.exists():
        state_file.unlink()


# 체인 선택 로직
def select_chain(task: str, config: dict) -> str:
    task_lower = task.lower()
    chains = config.get("chains", {})

    # O(n²) → O(n) 최적화: 키워드를 set으로 전처리
    for chain_name, chain_cfg in chains.items():
        triggers = chain_cfg.get("triggers", {})
        keywords = triggers.get("keywords", [])
        keyword_set = {kw.lower() for kw in keywords}  # 전처리

        # 단일 루프로 체크
        if any(kw in task_lower for kw in keyword_set):
            return chain_name

    return config.get("defaults", {}).get("fallback_chain", "FULL")


# v3: 인덱스 기반 다음 역할 결정
def get_next_role_by_index(state: dict) -> tuple[Optional[str], Optional[int]]:
    """인덱스 기반으로 다음 역할과 인덱스 반환"""
    chain_roles = state.get("chain_roles", [])
    if not chain_roles:
        return None, None

    current_index = state.get("current_index", 0)
    completed_indices = set(state.get("completed_indices", []))

    # 현재 인덱스부터 순회
    for i in range(current_index, len(chain_roles)):
        if i not in completed_indices:
            return chain_roles[i], i

    return None, None  # 모든 역할 완료


# v3: 분기 설정 조회 (max_loops 포함)
def get_branch_config(role: str, config: dict, chain_name: str) -> Optional[dict]:
    """분기 설정 반환 (from, to, condition, max_loops)"""
    chains = config.get("chains", {})
    chain = chains.get(chain_name, {})
    branches = chain.get("branches", [])

    for branch in branches:
        if branch.get("from") == role:
            return branch

    return None


# v3: 분기 조건 체크
def check_branch_condition(role: str, result: str, config: dict, chain_name: str) -> Optional[dict]:
    """
    결과가 분기 조건을 만족하면 분기 설정 반환

    condition은 문자열 또는 배열 지원:
    - 문자열: "reject" → result에 "reject" 포함 시 분기
    - 배열: ["reject", "반려", "거절"] → 하나라도 포함 시 분기
    """
    branch_config = get_branch_config(role, config, chain_name)
    if not branch_config:
        return None

    condition = branch_config.get("condition", "")
    result_lower = result.lower()

    # 배열 지원
    if isinstance(condition, list):
        for cond in condition:
            if cond.lower() in result_lower:
                return branch_config
        return None

    # 문자열
    if condition.lower() in result_lower:
        return branch_config

    return None


# v3: Sage 거부 체크
def check_sage_rejection(role: str, result: str) -> bool:
    """Sage 역할의 거부 여부 확인"""
    if role != "sage":
        return False

    rejection_keywords = ["불가", "rejected", "거부", "기각", "반려"]
    result_lower = result.lower()
    return any(kw in result_lower for kw in rejection_keywords)


# v3.1: Exit Conditions 체크 (config.yaml에서 로드)
def check_exit_condition(role: str, result: str, config: dict, chain_name: str) -> Optional[dict]:
    """즉시 종료 조건 확인"""
    chains = config.get("chains", {})
    chain = chains.get(chain_name, {})
    exit_conditions = chain.get("exit_conditions", [])

    result_lower = result.lower()
    for cond in exit_conditions:
        if cond.get("role") == role:
            keywords = cond.get("keywords", [])
            if any(kw.lower() in result_lower for kw in keywords):
                return cond

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Sage Orchestrator v3")
    parser.add_argument("task", nargs="?", help="작업 설명")
    parser.add_argument("--complete", metavar="ROLE", help="역할 완료 보고")
    parser.add_argument("--result", default="", help="역할 실행 결과 (분기/거부 판단용)")
    parser.add_argument("--status", action="store_true", help="현재 상태 출력")
    parser.add_argument("--reset", action="store_true", help="상태 초기화")

    args = parser.parse_args()
    config = load_config()
    state = load_state()

    # 상태 초기화
    if args.reset:
        clear_state()
        clear_current_session()  # v3.2
        print("RESET: OK")
        return

    # 상태 출력
    if args.status:
        chain_type = state.get("chain_type") or state.get("chain")
        if chain_type:
            completed_indices = state.get("completed_indices", [])
            chain_roles = state.get("chain_roles", [])
            branch_active = state.get("branch_active")

            # v3.1: 종료 상태 확인
            if state.get("exit_signal") and not state.get("active", True):
                exit_reason = state.get("exit_reason", "체인 종료")
                completed_names = [chain_roles[i] for i in completed_indices if i < len(chain_roles)]
                print(f"CHAIN: {chain_type}")
                print(f"STATUS: exited")
                print(f"REASON: {exit_reason}")
                print(f"COMPLETED: {', '.join(completed_names) or 'none'}")
                return

            print(f"CHAIN: {chain_type}")
            print(f"PHASE: {len(completed_indices)}/{len(chain_roles)}")

            # 완료된 역할 표시 (인덱스 기반)
            completed_names = [chain_roles[i] for i in completed_indices if i < len(chain_roles)]
            print(f"COMPLETED: {', '.join(completed_names) or 'none'}")

            # 분기 상태
            if branch_active:
                branch_loops = state.get("branch_loops", {})
                print(f"BRANCH_ACTIVE: {branch_active}")
                print(f"BRANCH_LOOPS: {branch_loops}")

            next_role, next_idx = get_next_role_by_index(state)
            if next_role:
                print(f"NEXT: {next_role} (index={next_idx})")
            elif branch_active:
                print(f"NEXT: {branch_active} (branch)")
            else:
                print("STATUS: all_complete")
        else:
            print("STATUS: idle")
        return

    # 역할 완료 처리
    if args.complete:
        role = args.complete
        chain_roles = state.get("chain_roles", [])
        chain_name = state.get("chain_type") or state.get("chain")

        # 상태 검증: 활성 세션이 있어야 함
        if not chain_roles or not state.get("active", False):
            print("ERROR: 활성 세션 없음. 먼저 작업을 시작하세요.")
            sys.exit(1)

        # === v3: Sage 거부 체크 ===
        if check_sage_rejection(role, args.result):
            state["exit_signal"] = True
            state["exit_reason"] = f"Sage 거부: {args.result}"
            state["active"] = False
            save_state(state)
            clear_current_session()  # v3.2
            print("REJECTED: Sage가 안건을 거부했습니다.")
            print(f"REASON: {args.result}")
            return

        # === v3.1: Exit Conditions 체크 (config 기반) ===
        exit_cond = check_exit_condition(role, args.result, config, chain_name)
        if exit_cond:
            state["exit_signal"] = True
            state["exit_reason"] = exit_cond.get("reason", f"{role} 종료 조건 충족")
            state["active"] = False
            save_state(state)
            clear_current_session()  # v3.2
            print(f"REJECTED: {exit_cond.get('reason', '종료 조건 충족')}")
            print(f"ROLE: {role}")
            print(f"RESULT: {args.result}")
            return

        # === v3: 분기 역할 완료 처리 ===
        branch_active = state.get("branch_active")
        if branch_active and role == branch_active:
            # 분기 역할 완료 → 원래 역할로 복귀
            return_index = state.get("branch_return_index")
            from_role = chain_roles[return_index] if return_index is not None else None

            # 분기 결과 확인: RESOLVED면 원래 역할 재실행, 아니면 분기 반복
            if "resolved" in args.result.lower() or "pass" in args.result.lower():
                # 문제 해결됨 → 원래 역할 재실행
                state["branch_active"] = None
                state["branch_return_index"] = None
                state["current_index"] = return_index  # 원래 위치로
                save_state(state)
                print(f"BRANCH_RESOLVED: {branch_active}")
                print(f"RETRY: {from_role} (index={return_index})")
                return
            else:
                # 문제 미해결 → 분기 반복 또는 종료
                branch_key = from_role
                branch_loops = state.get("branch_loops", {})
                current_loops = branch_loops.get(branch_key, 0)

                # max_loops 체크
                branch_config = get_branch_config(from_role, config, chain_name)
                max_loops = branch_config.get("max_loops", 2) if branch_config else 2

                if current_loops >= max_loops:
                    # 최대 반복 초과 → 체인 종료
                    state["exit_signal"] = True
                    state["exit_reason"] = f"분기 최대 횟수 초과: {branch_active} ({current_loops}/{max_loops})"
                    state["active"] = False
                    save_state(state)
                    clear_current_session()  # v3.2
                    print(f"REJECTED: 분기 최대 횟수 초과 ({current_loops}/{max_loops})")
                    print(f"BRANCH: {branch_active}")
                    return
                else:
                    # 분기 반복 (카운트 증가)
                    branch_loops[branch_key] = current_loops + 1
                    state["branch_loops"] = branch_loops
                    save_state(state)
                    print(f"BRANCH_RETRY: {branch_active}")
                    print(f"LOOP: {current_loops + 1}/{max_loops}")
                    return

        # === 일반 역할 완료 처리 ===
        current_index = state.get("current_index", 0)
        completed_indices = state.get("completed_indices", [])

        # === v3: 분기 조건 체크 (완료 처리 전에!) ===
        branch_config = check_branch_condition(role, args.result, config, chain_name)
        if branch_config:
            branch_to = branch_config.get("to")
            max_loops = branch_config.get("max_loops", 2)

            # 분기 횟수 증가
            branch_loops = state.get("branch_loops", {})
            branch_key = role
            current_loops = branch_loops.get(branch_key, 0) + 1
            branch_loops[branch_key] = current_loops
            state["branch_loops"] = branch_loops

            # max_loops 초과 체크
            if current_loops > max_loops:
                state["exit_signal"] = True
                state["exit_reason"] = f"분기 최대 횟수 초과: {branch_to} ({current_loops}/{max_loops})"
                state["active"] = False
                save_state(state)
                clear_current_session()  # v3.2
                print(f"REJECTED: 분기 최대 횟수 초과 ({current_loops}/{max_loops})")
                return

            # 분기 활성화 (원래 위치 저장, 완료로 표시하지 않음!)
            state["branch_active"] = branch_to
            state["branch_return_index"] = current_index
            save_state(state)
            print(f"BRANCH: {branch_to}")
            print(f"LOOP: {current_loops}/{max_loops}")
            print(f"RETURN_TO: {role} (index={current_index})")
            return

        # 분기 없음 → 역할 완료 처리
        # 현재 역할이 체인의 현재 인덱스와 일치하는지 확인
        if current_index < len(chain_roles) and chain_roles[current_index] == role:
            if current_index not in completed_indices:
                completed_indices.append(current_index)
                state["completed_indices"] = completed_indices

                # 하위 호환: completed_roles도 업데이트
                completed_roles = state.get("completed_roles", [])
                completed_roles.append(f"{role}#{current_index}")
                state["completed_roles"] = completed_roles

        # 다음 역할으로 진행
        state["current_index"] = current_index + 1
        next_role, next_idx = get_next_role_by_index(state)
        state["current_role"] = next_role

        # 모든 역할 완료 체크
        if next_role is None:
            state["exit_signal"] = True
            state["exit_reason"] = "모든 역할 완료"
            state["active"] = False
            save_state(state)
            clear_current_session()  # v3.2
            print("APPROVED: 모든 역할 완료")
            return

        save_state(state)
        print(f"NEXT: {next_role} (index={next_idx})")
        return

    # 새 작업 시작
    if args.task:
        # v3.2: 새 세션 생성 (기존 세션 무시)
        session_id = get_session_id(create_new=True)
        set_current_session(session_id)

        # 체인 선택
        chain = select_chain(args.task, config)

        # 체인 역할 목록 조회
        chains = config.get("chains", {})
        chain_def = chains.get(chain, {})
        roles = chain_def.get("roles", [])

        # v3: 인덱스 기반 상태 구조
        state = {
            "session_id": session_id,
            "task": args.task,
            "chain_type": chain,
            "chain": chain,  # 하위 호환
            "chain_roles": roles,
            "current_index": 0,  # v3
            "current_role": roles[0] if roles else None,
            "completed_indices": [],  # v3
            "completed_roles": [],  # 하위 호환
            "completed": [],  # 하위 호환
            "role_outputs": {},
            "active": True,
            "exit_signal": False,
            "started_at": datetime.now().isoformat(),
            "loop_count": 0,
            # v3: 분기 상태
            "branch_active": None,
            "branch_return_index": None,
            "branch_loops": {},
        }
        save_state(state)

        # 첫 번째 역할
        next_role, next_idx = get_next_role_by_index(state)

        # 출력
        print(f"SESSION: {session_id}")
        print(f"CHAIN: {chain}")
        print(f"TOTAL_PHASES: {len(roles)}")
        if next_role:
            print(f"NEXT: {next_role} (index={next_idx})")

        # TODO JSON 출력 (Claude가 TodoWrite 호출하도록 강제)
        todos = generate_todos(roles)
        print("TODO_REQUIRED:")
        print(json.dumps({"todos": todos}, ensure_ascii=False))
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
