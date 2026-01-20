# Sage Loop Session State Management
# 세션 상태 관리 및 Phase 전환 추적

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class SageSessionState:
    """
    Sage Loop 세션 상태 관리

    - 17단계 Phase 진행 상태 추적
    - Phase 10, 14 재시도 횟수 공유 (max 3회)
    - Phase별 출력 데이터 저장
    """

    session_id: str
    current_phase: int = 1
    total_retry_count: int = 0  # Phase 10, 14 공유
    max_retries: int = 3

    # Phase별 완료 상태
    phase_completed: dict = field(
        default_factory=lambda: {i: False for i in range(1, 18)}
    )

    # Phase별 출력 데이터
    phase_outputs: dict = field(default_factory=dict)

    # 타임스탬프
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # TodoWrite 상태
    todos: list = field(default_factory=list)

    # Ideator 아이디어
    ideas: list = field(default_factory=list)

    # Analyst 순위
    ranked_ideas: list = field(default_factory=list)

    def complete_phase(self, phase: int, output: Any):
        """Phase 완료 처리"""
        self.phase_completed[phase] = True
        self.phase_outputs[phase] = output
        self.current_phase = phase + 1
        self.last_updated = datetime.now()

    def reset_for_restart(self):
        """Phase 1 재시작을 위한 리셋"""
        self.current_phase = 1
        self.total_retry_count += 1
        self.phase_completed = {i: False for i in range(1, 18)}
        self.phase_outputs = {}
        self.todos = []
        self.ideas = []
        self.ranked_ideas = []
        self.last_updated = datetime.now()

    def can_retry(self) -> bool:
        """재시도 가능 여부 (max 3회)"""
        return self.total_retry_count < self.max_retries

    def get_phase_output(self, phase: int) -> Optional[Any]:
        """특정 Phase 출력 조회"""
        return self.phase_outputs.get(phase)

    def is_phase_completed(self, phase: int) -> bool:
        """특정 Phase 완료 여부"""
        return self.phase_completed.get(phase, False)
