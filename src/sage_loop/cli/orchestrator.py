#!/usr/bin/env python3
"""
Sage Orchestrator v4 - 병렬 실행 지원

주요 변경:
- 병렬 그룹 지원 (좌의정/우의정 동시 실행)
- 명확한 상태 머신
- 간결한 CLI 인터페이스
- 결과 병합 로직

사용법:
  python orchestrator_v4.py "새 기능 개발"           # 체인 시작
  python orchestrator_v4.py --complete ideator      # 역할 완료
  python orchestrator_v4.py --complete left-state-councilor,right-state-councilor  # 병렬 완료
  python orchestrator_v4.py --status                # 상태 확인
  python orchestrator_v4.py --reset                 # 초기화
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import yaml

# 세션 ID 생성은 session.py에서 통합 관리
from ..session import generate_session_id as _generate_session_id


# =============================================================================
# Constants
# =============================================================================

STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))
CONFIG_PATH = Path(__file__).resolve().parent / "config_v4.yaml"
CURRENT_SESSION_FILE = STATE_DIR / "sage_current_session"


class ChainStatus(str, Enum):
    """체인 상태"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_PARALLEL = "waiting_parallel"  # 병렬 그룹 완료 대기
    BRANCHING = "branching"
    APPROVED = "approved"
    REJECTED = "rejected"


# 역할 설명 (TodoWrite용)
ROLE_INFO = {
    "yeong-ui-jeong": ("영의정 심의", "영의정 심의 중"),
    "ideator": ("아이디어 생성", "아이디어 생성 중"),
    "analyst": ("분석/선별", "분석 중"),
    "critic": ("위험/결함 비판", "비판 검토 중"),
    "censor": ("RULES 사전 봉쇄", "규칙 검증 중"),
    "academy": ("학술 자문", "학술 자문 중"),
    "architect": ("설계 수립", "설계 중"),
    "left-state-councilor": ("내정 검토", "내정 검토 중"),
    "right-state-councilor": ("실무 검토", "실무 검토 중"),
    "executor": ("구현", "구현 중"),
    "inspector": ("감찰", "감찰 중"),
    "validator": ("검증", "검증 중"),
    "historian": ("기록", "기록 중"),
    "reflector": ("회고", "회고 중"),
    "improver": ("개선", "개선 중"),
    "feasibility-checker": ("실현 가능성 검증", "가능성 검증 중"),
    "constraint-enforcer": ("조건부 승인 조건 해결", "조건 해결 중"),
    "policy-keeper": ("정책 관리", "정책 검토 중"),
    # 6조 낭청 (ideator)
    "ideator-personnel": ("이조 아이디어 (인사)", "이조 아이디어 생성 중"),
    "ideator-finance": ("호조 아이디어 (재정)", "호조 아이디어 생성 중"),
    "ideator-rites": ("예조 아이디어 (문화)", "예조 아이디어 생성 중"),
    "ideator-military": ("병조 아이디어 (운영)", "병조 아이디어 생성 중"),
    "ideator-justice": ("형조 아이디어 (검증)", "형조 아이디어 생성 중"),
    "ideator-works": ("공조 아이디어 (인프라)", "공조 아이디어 생성 중"),
    # 6조 판서 (analyst)
    "analyst-personnel": ("이조 분석 (인사)", "이조 분석 중"),
    "analyst-finance": ("호조 분석 (재정)", "호조 분석 중"),
    "analyst-rites": ("예조 분석 (문화)", "예조 분석 중"),
    "analyst-military": ("병조 분석 (운영)", "병조 분석 중"),
    "analyst-justice": ("형조 분석 (검증)", "형조 분석 중"),
    "analyst-works": ("공조 분석 (인프라)", "공조 분석 중"),
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PhaseItem:
    """체인의 단일 페이즈 (순차 또는 병렬)"""
    index: int
    roles: list[str]  # 단일 역할이면 [role], 병렬이면 [role1, role2]
    is_parallel: bool = False

    @property
    def display_name(self) -> str:
        if self.is_parallel:
            return f"[{' + '.join(self.roles)}]"
        return self.roles[0]


@dataclass
class ChainState:
    """체인 실행 상태"""
    session_id: str
    task: str
    chain_name: str
    phases: list[dict]  # PhaseItem을 dict로 저장

    status: str = ChainStatus.IDLE.value
    current_phase: int = 0

    # 완료 추적
    completed_phases: list[int] = field(default_factory=list)
    pending_roles: list[str] = field(default_factory=list)  # 병렬 대기 중
    completed_parallel: list[str] = field(default_factory=list)  # 병렬 중 완료된 것

    # 분기 상태
    branch_active: Optional[str] = None
    branch_return_phase: Optional[int] = None
    branch_loops: dict = field(default_factory=dict)

    # 역할별 결과 저장
    role_results: dict = field(default_factory=dict)

    # 조건부 승인 조건 수집 (방안 B)
    pending_conditions: list = field(default_factory=list)

    # 메타데이터
    started_at: str = ""
    exit_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChainState":
        return cls(**data)


# =============================================================================
# Session Management
# =============================================================================


def get_session_id(create_new: bool = False) -> str:
    """세션 ID 획득"""
    if not create_new:
        # 1. 환경 변수
        env_id = os.environ.get("SAGE_SESSION_ID")
        if env_id:
            return env_id

        # 2. 세션 파일
        if CURRENT_SESSION_FILE.exists():
            stored = CURRENT_SESSION_FILE.read_text().strip()
            if stored:
                return stored

    # 3. 새 ID 생성
    new_id = _generate_session_id()
    os.environ["SAGE_SESSION_ID"] = new_id
    return new_id


def set_session(session_id: str) -> None:
    CURRENT_SESSION_FILE.write_text(session_id)
    os.environ["SAGE_SESSION_ID"] = session_id


def clear_session() -> None:
    if CURRENT_SESSION_FILE.exists():
        CURRENT_SESSION_FILE.unlink()
    os.environ.pop("SAGE_SESSION_ID", None)


def get_state_path() -> Path:
    return STATE_DIR / f"sage_state_{get_session_id()}.json"


# =============================================================================
# State Persistence (File Lock + Atomic Write)
# =============================================================================

def load_state_unsafe() -> Optional[ChainState]:
    """락 없이 상태 읽기 (내부용)"""
    path = get_state_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return ChainState.from_dict(data)
    except (json.JSONDecodeError, TypeError):
        return None


def load_state() -> Optional[ChainState]:
    """상태 읽기 (외부용, 호환성 유지)"""
    return load_state_unsafe()


def save_state_atomic(state: ChainState) -> None:
    """원자적 저장 (temp → rename)"""
    path = get_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        os.rename(tmp_path, path)  # POSIX에서 원자적
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def save_state(state: ChainState) -> None:
    """상태 저장 (외부용, 호환성 유지)"""
    save_state_atomic(state)


def atomic_state_update(
    update_fn: Callable[[ChainState], ChainState],
    max_retries: int = 3
) -> ChainState:
    """원자적 상태 업데이트 (파일 락 + atomic write)

    Args:
        update_fn: 상태를 받아 수정된 상태를 반환하는 함수
        max_retries: 락 획득 최대 재시도 횟수

    Returns:
        업데이트된 ChainState

    Raises:
        ValueError: 활성 세션이 없을 때
        RuntimeError: 락 획득 실패 시
    """
    path = get_state_path()
    lock_path = path.with_suffix('.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(max_retries):
        try:
            with open(lock_path, 'w') as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    # Read current state
                    state = load_state_unsafe()
                    if state is None:
                        raise ValueError("No active session")

                    # Apply update
                    state = update_fn(state)

                    # Atomic write
                    save_state_atomic(state)
                    return state
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        except BlockingIOError:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # 100ms, 200ms, 300ms
            else:
                raise RuntimeError(f"Failed to acquire state lock after {max_retries} attempts")

    # Should not reach here
    raise RuntimeError("Unexpected error in atomic_state_update")


def clear_state() -> None:
    """상태 파일 삭제"""
    path = get_state_path()
    lock_path = path.with_suffix('.lock')
    if path.exists():
        path.unlink()
    if lock_path.exists():
        lock_path.unlink()


# =============================================================================
# Config Loading
# =============================================================================

def load_config() -> dict:
    # v4 config 우선, 없으면 기존 config 사용
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text()) or {}

    # fallback to old config
    old_config = CONFIG_PATH.parent / "config.yaml"
    if old_config.exists():
        return yaml.safe_load(old_config.read_text()) or {}

    return {}


def parse_chain_roles(roles_config: list) -> list[PhaseItem]:
    """
    체인 설정을 PhaseItem 리스트로 변환

    지원 형식:
    - "role"                    → 순차 실행
    - ["role1", "role2"]        → 병렬 실행
    - {"parallel": ["r1", "r2"]} → 명시적 병렬
    """
    phases = []
    idx = 0

    for item in roles_config:
        if isinstance(item, str):
            # 단일 역할 (순차)
            phases.append(PhaseItem(index=idx, roles=[item], is_parallel=False))
        elif isinstance(item, list):
            # 리스트 = 병렬
            phases.append(PhaseItem(index=idx, roles=item, is_parallel=True))
        elif isinstance(item, dict):
            # 명시적 parallel 키
            if "parallel" in item:
                phases.append(PhaseItem(index=idx, roles=item["parallel"], is_parallel=True))
            elif "sequential" in item:
                # 순차 그룹 (개별 phase로 분리)
                for role in item["sequential"]:
                    phases.append(PhaseItem(index=idx, roles=[role], is_parallel=False))
                    idx += 1
                continue
        idx += 1

    return phases


def select_chain(task: str, config: dict) -> str:
    """작업에 맞는 체인 선택"""
    task_lower = task.lower()
    chains = config.get("chains", {})

    for name, cfg in chains.items():
        triggers = cfg.get("triggers", {})
        keywords = [k.lower() for k in triggers.get("keywords", [])]
        if any(kw in task_lower for kw in keywords):
            return name

    return config.get("defaults", {}).get("fallback_chain", "FULL")


# =============================================================================
# Branch Logic
# =============================================================================

def check_branch(role: str, result: str, config: dict, chain_name: str) -> Optional[dict]:
    """분기 조건 확인"""
    chains = config.get("chains", {})
    chain = chains.get(chain_name, {})
    branches = chain.get("branches", [])

    result_lower = result.lower()
    for branch in branches:
        if branch.get("from") != role:
            continue

        conditions = branch.get("condition", [])
        if isinstance(conditions, str):
            conditions = [conditions]

        if any(c.lower() in result_lower for c in conditions):
            return branch

    return None


def check_exit(role: str, result: str, config: dict, chain_name: str) -> Optional[dict]:
    """즉시 종료 조건 확인"""
    chains = config.get("chains", {})
    chain = chains.get(chain_name, {})
    exits = chain.get("exit_conditions", [])

    result_lower = result.lower()
    for cond in exits:
        if cond.get("role") != role:
            continue

        keywords = cond.get("keywords", [])
        if any(kw.lower() in result_lower for kw in keywords):
            return cond

    return None


# =============================================================================
# Core Logic
# =============================================================================

def start_chain(task: str, config: dict) -> ChainState:
    """새 체인 시작"""
    session_id = _generate_session_id()
    set_session(session_id)

    chain_name = select_chain(task, config)
    chains = config.get("chains", {})
    chain_cfg = chains.get(chain_name, {})
    roles_config = chain_cfg.get("roles", [])

    phases = parse_chain_roles(roles_config)

    state = ChainState(
        session_id=session_id,
        task=task,
        chain_name=chain_name,
        phases=[asdict(p) for p in phases],
        status=ChainStatus.RUNNING.value,
        current_phase=0,
        started_at=datetime.now().isoformat(),
    )

    # 첫 phase 설정
    if phases:
        first = phases[0]
        if first.is_parallel:
            state.pending_roles = first.roles.copy()
            state.status = ChainStatus.WAITING_PARALLEL.value
        else:
            state.pending_roles = first.roles.copy()

    save_state(state)
    return state


def _extract_conditions(result: str) -> list[str]:
    """조건부 승인에서 조건들을 추출"""
    import re
    conditions = []
    # 패턴: "조건부승인: 조건1, 조건2" 또는 "conditional: cond1, cond2"
    patterns = [
        r"조건부\s*승인[:\s]+(.+?)(?:\n|$)",
        r"conditional[:\s]+(.+?)(?:\n|$)",
        r"조건[:\s]+(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, result, re.IGNORECASE)
        for match in matches:
            # 쉼표나 세미콜론으로 분리
            parts = re.split(r"[,;]", match)
            conditions.extend([p.strip() for p in parts if p.strip()])
    return conditions


def _complete_role_impl(state: ChainState, roles: list[str], results: dict[str, str], config: dict) -> ChainState:
    """역할 완료 처리 (내부 구현, 저장 없음)"""
    phase_data = state.phases[state.current_phase]
    phase = PhaseItem(**phase_data)

    # 결과 저장 + 조건부 승인 조건 수집 (방안 B)
    for role, result in results.items():
        state.role_results[role] = result
        # 조건부 승인 조건 추출
        conditions = _extract_conditions(result)
        if conditions:
            for cond in conditions:
                state.pending_conditions.append({
                    "from_role": role,
                    "condition": cond,
                })

    # 분기/종료 체크 (각 역할별)
    for role, result in results.items():
        # 종료 조건 체크
        exit_cond = check_exit(role, result, config, state.chain_name)
        if exit_cond:
            state.status = ChainStatus.REJECTED.value
            state.exit_reason = exit_cond.get("reason", f"{role} 종료 조건")
            clear_session()
            return state

        # 분기 조건 체크
        branch = check_branch(role, result, config, state.chain_name)
        if branch:
            branch_to = branch.get("to")
            max_loops = branch.get("max_loops", 2)

            # 분기 횟수 체크
            loop_key = f"{role}->{branch_to}"
            current_loops = state.branch_loops.get(loop_key, 0) + 1
            state.branch_loops[loop_key] = current_loops

            if current_loops > max_loops:
                state.status = ChainStatus.REJECTED.value
                state.exit_reason = f"분기 최대 횟수 초과: {loop_key} ({current_loops}/{max_loops})"
                clear_session()
                return state

            # 분기 활성화
            state.branch_active = branch_to
            state.branch_return_phase = state.current_phase
            state.status = ChainStatus.BRANCHING.value
            state.pending_roles = [branch_to]
            return state

    # 병렬 그룹 처리
    if phase.is_parallel:
        for role in roles:
            if role in state.pending_roles:
                state.pending_roles.remove(role)
                state.completed_parallel.append(role)

        # 아직 대기 중인 역할이 있으면 유지
        if state.pending_roles:
            return state

        # 모든 병렬 역할 완료
        state.completed_parallel = []

    # 분기 복귀 처리
    if state.branch_active:
        state.branch_active = None
        state.current_phase = state.branch_return_phase
        state.branch_return_phase = None
        # 원래 phase 재실행
        phase_data = state.phases[state.current_phase]
        phase = PhaseItem(**phase_data)
        state.pending_roles = phase.roles.copy()
        state.status = ChainStatus.RUNNING.value
        return state

    # 다음 phase로 진행
    state.completed_phases.append(state.current_phase)
    state.current_phase += 1

    # 체인 완료 체크
    if state.current_phase >= len(state.phases):
        state.status = ChainStatus.APPROVED.value
        state.exit_reason = "모든 역할 완료"
        clear_session()
        return state

    # 다음 phase 설정
    next_phase_data = state.phases[state.current_phase]
    next_phase = PhaseItem(**next_phase_data)

    # 방안 B: constraint-enforcer는 조건이 있을 때만 실행
    if "constraint-enforcer" in next_phase.roles and not state.pending_conditions:
        # 조건 없으면 스킵
        state.completed_phases.append(state.current_phase)
        state.current_phase += 1
        if state.current_phase >= len(state.phases):
            state.status = ChainStatus.APPROVED.value
            state.exit_reason = "모든 역할 완료"
            clear_session()
            return state
        next_phase_data = state.phases[state.current_phase]
        next_phase = PhaseItem(**next_phase_data)

    state.pending_roles = next_phase.roles.copy()

    if next_phase.is_parallel:
        state.status = ChainStatus.WAITING_PARALLEL.value
    else:
        state.status = ChainStatus.RUNNING.value

    return state


def complete_role_atomic(roles: list[str], results: dict[str, str], config: dict) -> ChainState:
    """역할 완료 처리 (원자적, 파일 락 적용)

    병렬 역할이 동시에 완료되어도 안전하게 상태 업데이트.
    """
    def do_complete(state: ChainState) -> ChainState:
        return _complete_role_impl(state, roles, results, config)

    return atomic_state_update(do_complete)


def complete_role(state: ChainState, roles: list[str], results: dict[str, str], config: dict) -> ChainState:
    """역할 완료 처리 (레거시 호환용)

    주의: 이 함수는 호환성을 위해 유지되지만, 병렬 실행 시
    complete_role_atomic()을 사용해야 합니다.
    """
    state = _complete_role_impl(state, roles, results, config)
    save_state(state)
    return state


# =============================================================================
# Output Formatting
# =============================================================================

def generate_todos(phases: list[PhaseItem]) -> list[dict]:
    """TodoWrite용 JSON 생성"""
    todos = []
    for i, phase in enumerate(phases, 1):
        if phase.is_parallel:
            roles_str = " + ".join(phase.roles)
            desc = f"병렬: {', '.join(ROLE_INFO.get(r, (r, r))[0] for r in phase.roles)}"
            active = f"{roles_str} 실행 중"
        else:
            role = phase.roles[0]
            desc, active = ROLE_INFO.get(role, (role, f"{role} 실행 중"))

        todos.append({
            "content": f"Phase {i}: {phase.display_name} - {desc}",
            "status": "pending",
            "activeForm": active,
        })
    return todos


def print_status(state: ChainState) -> None:
    """상태 출력"""
    print(f"SESSION: {state.session_id}")
    print(f"CHAIN: {state.chain_name}")
    print(f"STATUS: {state.status}")
    print(f"PHASE: {state.current_phase + 1}/{len(state.phases)}")

    if state.completed_phases:
        completed_names = []
        for idx in state.completed_phases:
            phase = PhaseItem(**state.phases[idx])
            completed_names.append(phase.display_name)
        print(f"COMPLETED: {', '.join(completed_names)}")

    if state.status == ChainStatus.WAITING_PARALLEL.value:
        print(f"PENDING_PARALLEL: {', '.join(state.pending_roles)}")
        if state.completed_parallel:
            print(f"COMPLETED_PARALLEL: {', '.join(state.completed_parallel)}")

    if state.branch_active:
        print(f"BRANCH_ACTIVE: {state.branch_active}")

    if state.status in (ChainStatus.APPROVED.value, ChainStatus.REJECTED.value):
        print(f"REASON: {state.exit_reason}")
    elif state.pending_roles:
        if len(state.pending_roles) > 1:
            print(f"NEXT_PARALLEL: {', '.join(state.pending_roles)}")
        else:
            print(f"NEXT: {state.pending_roles[0]}")


def print_start(state: ChainState) -> None:
    """시작 출력"""
    phases = [PhaseItem(**p) for p in state.phases]

    print(f"SESSION: {state.session_id}")
    print(f"CHAIN: {state.chain_name}")
    print(f"TOTAL_PHASES: {len(phases)}")

    if state.pending_roles:
        if len(state.pending_roles) > 1:
            print(f"NEXT_PARALLEL: {', '.join(state.pending_roles)}")
        else:
            print(f"NEXT: {state.pending_roles[0]}")

    print("TODO_REQUIRED:")
    print(json.dumps({"todos": generate_todos(phases)}, ensure_ascii=False))


def print_complete(state: ChainState) -> None:
    """완료 후 출력"""
    if state.status == ChainStatus.APPROVED.value:
        print("APPROVED: 모든 역할 완료")
        return

    if state.status == ChainStatus.REJECTED.value:
        print(f"REJECTED: {state.exit_reason}")
        return

    if state.status == ChainStatus.BRANCHING.value:
        loop_key = list(state.branch_loops.keys())[-1] if state.branch_loops else ""
        loops = state.branch_loops.get(loop_key, 1)
        print(f"BRANCH: {state.branch_active}")
        print(f"LOOP: {loops}")
        return

    if state.status == ChainStatus.WAITING_PARALLEL.value:
        if state.completed_parallel:
            print(f"PARALLEL_PROGRESS: {', '.join(state.completed_parallel)} 완료")
        print(f"PENDING: {', '.join(state.pending_roles)}")
        return

    # 일반 진행
    if state.pending_roles:
        if len(state.pending_roles) > 1:
            print(f"NEXT_PARALLEL: {', '.join(state.pending_roles)}")
        else:
            print(f"NEXT: {state.pending_roles[0]}")

    # 방안 B: 조건부 승인 조건 출력
    if state.pending_conditions and "constraint-enforcer" in state.pending_roles:
        print("PENDING_CONDITIONS:")
        for cond in state.pending_conditions:
            print(f"  - [{cond['from_role']}] {cond['condition']}")


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sage Orchestrator v4 - 병렬 실행 지원",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  %(prog)s "새 기능 개발"              체인 시작
  %(prog)s --complete ideator          역할 완료
  %(prog)s --complete "left,right"     병렬 역할 완료
  %(prog)s --status                    상태 확인
  %(prog)s --reset                     초기화
        """
    )

    parser.add_argument("task", nargs="?", help="작업 설명 (체인 시작)")
    parser.add_argument("--complete", "-c", metavar="ROLES",
                       help="완료된 역할 (쉼표로 구분)")
    parser.add_argument("--result", "-r", default="pass",
                       help="역할 실행 결과")
    parser.add_argument("--status", "-s", action="store_true",
                       help="현재 상태 출력")
    parser.add_argument("--reset", action="store_true",
                       help="상태 초기화")

    args = parser.parse_args()
    config = load_config()

    # 초기화
    if args.reset:
        clear_state()
        clear_session()
        print("RESET: OK")
        return

    # 상태 확인
    if args.status:
        state = load_state()
        if state:
            print_status(state)
        else:
            print("STATUS: idle")
        return

    # 역할 완료 (원자적 업데이트)
    if args.complete:
        # 쉼표로 구분된 역할 파싱
        roles = [r.strip() for r in args.complete.split(",")]
        results = {role: args.result for role in roles}

        try:
            state = complete_role_atomic(roles, results, config)
            print_complete(state)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        except RuntimeError as e:
            print(f"LOCK_ERROR: {e}")
            sys.exit(1)
        return

    # 새 체인 시작
    if args.task:
        state = start_chain(args.task, config)
        print_start(state)
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
