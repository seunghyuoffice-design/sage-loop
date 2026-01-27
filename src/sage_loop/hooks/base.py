# Sage Loop Hooks - Base Classes
# 17단계 Phase Hook 베이스 클래스

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any


class PhaseStatus(Enum):
    """Phase 처리 상태"""
    PROCEED = "proceed"      # 다음 Phase로 진행
    RETRY = "retry"          # 현재 Phase 재시도
    RESTART = "restart"      # Phase 1부터 재시작
    BLOCK = "block"          # 차단 (진행 불가)
    ABORT = "abort"          # 완전 중단


@dataclass
class PhaseResult:
    """Phase 처리 결과"""
    status: PhaseStatus
    next_phase: Optional[int]
    reason: Optional[str] = None
    retry_count: int = 0
    data: Optional[Any] = None


class PhaseHook(ABC):
    """
    Phase Hook 베이스 클래스

    각 Phase는 다음을 정의해야 함:
    - phase_number: Phase 번호 (1-17)
    - role_name: 역할 이름
    - allowed_actions: 허용된 행동 목록
    - forbidden_actions: 금지된 행동 목록
    - enforcement_message: 대충 마무리 방지용 독설
    """

    phase_number: int
    role_name: str
    allowed_actions: list[str]
    forbidden_actions: list[str]
    enforcement_message: str = ""  # 대충 마무리 방지용 독설

    @abstractmethod
    def validate_input(self, session_state: dict) -> PhaseResult:
        """
        Phase 진입 조건 검증
        이전 Phase가 완료되었는지 확인
        """
        pass

    @abstractmethod
    def validate_output(self, output: dict) -> PhaseResult:
        """
        Phase 완료 조건 검증
        출력이 요구사항을 충족하는지 확인
        """
        pass

    @abstractmethod
    def check_scope(self, action: str, tool: str) -> bool:
        """
        역할 범위 내 행동인지 확인
        범위 이탈 시 False 반환 → BLOCK
        """
        pass

    def check_thinking(self, thinking: str) -> bool:
        """
        사고 과정에서 금지 패턴 감지
        기본: 허용 (True)
        오버라이드하여 금지 패턴 정의 가능
        """
        return True
