#!/usr/bin/env python3
"""
Phase 3: Analyst(선지자) - 실현가능성 순위 나열

트리거: Phase 2 완료 후
허용: 선별, 정리, 순위 나열
금지: 새 아이디어 추가, 비판, 설계
완료 조건: 모든 아이디어에 순위 부여됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase03Analyst(PhaseHook):
    """
    Phase 3: Analyst(선지자) - 실현가능성 순위 나열

    역할: 아이디어를 선별하고 순위를 매긴다.
    페르소나: 냉정한 분석가, 수치화 선호
    말투: "실현가능성 순위", "1위는...", "가장 현실적인 것은"
    """

    phase_number = 3
    role_name = "analyst"

    allowed_actions = [
        "rank_ideas",           # 순위 나열
        "classify_feasibility", # 실현가능성 분류
        "select_top",           # 상위 선별
        "organize",             # 정리
        "categorize",           # 분류
    ]

    forbidden_actions = [
        "generate_ideas",       # 새 아이디어 추가 금지
        "criticize",            # 비판 금지 (Critic 영역)
        "design",               # 설계 금지 (Architect 영역)
        "execute",              # 실행 금지
        "find_risks",           # 위험 찾기 금지 (Critic 영역)
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 2에서 아이디어 10개 이상 전달되었는지 확인"""
        ideas = session_state.get("ideas", [])
        if len(ideas) >= 10:
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=3)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason=f"아이디어 부족: {len(ideas)}개 < 10개"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """모든 아이디어에 순위가 부여되었는지 확인"""
        ranked_ideas = output.get("ranked_ideas", [])

        # 순위 검증
        has_all_ranks = all(
            "rank" in idea and isinstance(idea["rank"], int)
            for idea in ranked_ideas
        )

        # 실현가능성 분류 검증
        has_feasibility = all(
            "feasibility" in idea
            for idea in ranked_ideas
        )

        if has_all_ranks and has_feasibility and len(ranked_ideas) > 0:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=4,
                reason="순위 나열 완료. 비조에게 위험을 검토하게 하라.",
                data={"ranked_ideas": ranked_ideas}
            )
        else:
            missing = []
            if not has_all_ranks:
                missing.append("순위")
            if not has_feasibility:
                missing.append("실현가능성")
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=3,
                reason=f"누락: {', '.join(missing)}. 모든 아이디어에 순위를 매기라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
