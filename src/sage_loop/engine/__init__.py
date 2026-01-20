"""Sage Engine - 체인 실행 및 역할 관리

Core Components:
    - ChainExecutor: 기존 체인 실행기 (순차)
    - RoleRunner: 역할 실행기
    - BranchHandler: 분기 처리

v2 Components (컨텍스트 효율화):
    - SageCommander: 지휘관 모드 (최소 컨텍스트)
    - TaskDispatcher: Task 기반 역할 디스패치
    - ContextCompactor: 역할 출력 압축
    - CompactCheckpoint: 체크포인트 관리
    - ParallelTaskRunner: 병렬 Task 실행기
"""

from .branch_handler import BranchHandler
from .chain_executor import ChainExecutor
from .compact_checkpoint import (
    CompactCheckpoint,
    SageCompactState,
    should_compact,
    create_compact_block,
    export_compact_yaml,
    restore_from_yaml,
    get_compact_yaml_for_session,
)
from .context_compactor import ContextCompactor, compact_output, prepare_role_input
from .parallel_task_runner import ParallelTaskRunner, run_parallel_tasks, get_parallel_roles_for
from .role_runner import RoleRunner
from .sage_commander import SageCommander, execute_sage_chain
from .task_dispatcher import TaskDispatcher, build_role_task

__all__ = [
    # Core
    "ChainExecutor",
    "RoleRunner",
    "BranchHandler",
    # v2 Components
    "SageCommander",
    "TaskDispatcher",
    "ContextCompactor",
    "CompactCheckpoint",
    "ParallelTaskRunner",
    # Convenience functions
    "execute_sage_chain",
    "build_role_task",
    "compact_output",
    "prepare_role_input",
    "should_compact",
    "create_compact_block",
    "run_parallel_tasks",
    "get_parallel_roles_for",
    # Claude Code Integration
    "SageCompactState",
    "export_compact_yaml",
    "restore_from_yaml",
    "get_compact_yaml_for_session",
]
