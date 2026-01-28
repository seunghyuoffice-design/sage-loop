# Sage Loop Hooks - 14-Phase System
# v4 TRIPLE SAGE (영의정 3회 호출: Phase 1, 9, 13)

from .base import PhaseHook, PhaseResult, PhaseStatus
from .session_state import SageSessionState

from .phase01_sage_intake import Phase01SageIntake
from .phase02_ideator import Phase02Ideator
from .phase03_analyst import Phase03Analyst
from .phase04_critic import Phase04Critic
from .phase05_censor import Phase05Censor
from .phase06_academy import Phase06Academy
from .phase07_architect import Phase07Architect
from .phase08_leftstate import Phase08LeftState
from .phase09_rightstate import Phase09RightState
from .phase10_sage_approval import Phase10SageApproval
from .phase11_executor import Phase11Executor
from .phase12_inspector import Phase12Inspector
from .phase13_validator import Phase13Validator
from .phase14_sage_final import Phase14SageFinal

PHASE_HOOKS = {
    1: Phase01SageIntake,
    2: Phase02Ideator,
    3: Phase03Analyst,
    4: Phase04Critic,
    5: Phase05Censor,
    6: Phase06Academy,
    7: Phase07Architect,
    8: Phase08LeftState,
    9: Phase09RightState,
    10: Phase10SageApproval,
    11: Phase11Executor,
    12: Phase12Inspector,
    13: Phase13Validator,
    14: Phase14SageFinal,
}

__all__ = [
    "PhaseHook",
    "PhaseResult",
    "PhaseStatus",
    "SageSessionState",
    "PHASE_HOOKS",
]
