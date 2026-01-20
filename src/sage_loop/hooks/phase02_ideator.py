#!/usr/bin/env python3
"""
Phase 2: Ideator(현인) - 아이디어 발산

트리거: Phase 1 완료 후
허용: 아이디어 발산, 가능성 나열
금지: 판단, 선별, 비판, 실행
완료 조건: 아이디어 10개 이상
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


IDEATOR_MIN_IDEAS = 10  # 최소 아이디어 개수


class Phase02Ideator(PhaseHook):
    """
    Phase 2: Ideator(현인) - 아이디어 발산

    역할: 판단 없이 가능성을 발산한다.
    페르소나: 철부지 아이디어뱅크, 자유로운 사고
    말투: "~할 수도 있고", "~도 가능하고", "~는 어떨까"
    """

    phase_number = 2
    role_name = "ideator"

    allowed_actions = [
        "generate_ideas",       # 아이디어 생성
        "list_possibilities",   # 가능성 나열
        "brainstorm",           # 브레인스토밍
        "explore",              # 탐색
        "imagine",              # 상상
    ]

    forbidden_actions = [
        "judge",                # 판단 금지
        "select",               # 선별 금지
        "criticize",            # 비판 금지
        "execute",              # 실행 금지
        "rank",                 # 순위 금지 (Analyst 영역)
        "evaluate",             # 평가 금지
        "reject",               # 거부 금지
    ]

    # 금지 사고 패턴 (판단 표현)
    forbidden_patterns = [
        "안 될 것 같다",
        "불가능하다",
        "어렵다",
        "이건 안 돼",
        "비현실적",
        "실현 가능성이 낮",
        "이건 좋고",
        "이건 나쁘고",
        "최선의",
        "최악의",
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 1 완료 확인"""
        if session_state.get("phase_completed", {}).get(1, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=2)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 1 (Sage 접수) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """아이디어 10개 이상 확인"""
        ideas = output.get("ideas", [])
        count = len(ideas)

        if count >= IDEATOR_MIN_IDEAS:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=3,
                reason=f"아이디어 {count}개 생성 완료. 선지자에게 선별을 맡기라.",
                data={"ideas": ideas}
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=2,
                reason=f"아이디어 {count}개 < 최소 {IDEATOR_MIN_IDEAS}개. 더 발산하라."
            )

    def check_thinking(self, thinking: str) -> bool:
        """사고 과정에서 금지 패턴 감지"""
        for pattern in self.forbidden_patterns:
            if pattern in thinking:
                return False  # BLOCK - 판단 표현 감지
        return True

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
