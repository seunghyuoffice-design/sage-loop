#!/usr/bin/env python3
"""
Phase 16: Reflector(회고관) - 회고

트리거: Phase 15 완료 후
허용: 회고, 교훈 도출
금지: 수정, 실행, 새 작업 시작
완료 조건: 교훈 도출됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase16Reflector(PhaseHook):
    """
    Phase 16: Reflector(회고관) - 회고

    역할: 과정을 회고하고 교훈을 도출한다.
    페르소나: 사려 깊은 회고자
    말투: "잘된 점", "아쉬운 점", "교훈", "다음에는"

    수정하지 않는다. 회고만 한다.
    """

    phase_number = 16
    role_name = "reflector"
    enforcement_message = "세션 전체를 봤다. 반복되는 병목이 보인다."

    # 강제 주입 메시지
    enforcement_message = "마무리에서 항상 밀도가 떨어진다."

    allowed_actions = [
        "reflect",              # 회고
        "extract_lessons",      # 교훈 도출
        "analyze_process",      # 과정 분석
        "identify_patterns",    # 패턴 식별
        "summarize",            # 요약
    ]

    forbidden_actions = [
        "modify",               # 수정 금지
        "execute",              # 실행 금지
        "start_new",            # 새 작업 시작 금지
        "fix",                  # 수정 금지
        "implement",            # 구현 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 15 완료 확인"""
        if session_state.get("phase_completed", {}).get(15, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=16)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 15 (Historian) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """교훈 도출 확인"""
        reflection = output.get("reflection", {})
        lessons = output.get("lessons", [])
        what_went_well = output.get("what_went_well", [])
        what_to_improve = output.get("what_to_improve", [])

        has_reflection = reflection or lessons or what_went_well or what_to_improve

        if has_reflection:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=17,
                reason="회고 완료. 개선관에게 개선점 제안을 맡기라.",
                data={
                    "reflection": reflection,
                    "lessons": lessons,
                    "what_went_well": what_went_well,
                    "what_to_improve": what_to_improve
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=16,
                reason="회고가 없다. 과정을 회고하고 교훈을 도출하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 수정 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        # 조회 도구만 허용
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return False
