#!/usr/bin/env python3
"""
Phase 4: Critic(비조) - 위험/논리/비용/결함 지적

트리거: Phase 3 완료 후
허용: 위험 지적, 논리 결함 발견, 비용 분석
금지: 설계, 대안 제시, 승인
완료 조건: 상위 아이디어에 대한 위험 목록 작성됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase04Critic(PhaseHook):
    """
    Phase 4: Critic(비조) - 위험/논리/비용/결함 지적

    역할: 위험과 결함만 지적한다. 해결책은 제시하지 않는다.
    페르소나: 까다로운 감사관, 악마의 변호인
    말투: "위험하다", "결함이 있다", "비용이 과다하다", "논리가 맞지 않다"
    """

    phase_number = 4
    role_name = "critic"
    enforcement_message = "위험·논리·비용·결함, 하나라도 빠지면 탄핵이다."

    allowed_actions = [
        "find_risks",           # 위험 찾기
        "find_flaws",           # 결함 찾기
        "analyze_cost",         # 비용 분석
        "check_logic",          # 논리 검증
        "question",             # 질문
        "challenge",            # 도전/반박
    ]

    forbidden_actions = [
        "design",               # 설계 금지 (Architect 영역)
        "suggest_alternative",  # 대안 제시 금지
        "approve",              # 승인 금지 (Sage 영역)
        "execute",              # 실행 금지
        "solve",                # 해결 금지
        "fix",                  # 수정 금지
    ]

    # 금지 사고 패턴 (해결책 제시)
    forbidden_patterns = [
        "이렇게 하면 된다",
        "대안으로",
        "해결책은",
        "고치면",
        "수정하면",
        "괜찮다",
        "문제없다",
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 3 완료 확인"""
        if session_state.get("phase_completed", {}).get(3, False):
            ranked_ideas = session_state.get("ranked_ideas", [])
            if len(ranked_ideas) > 0:
                return PhaseResult(status=PhaseStatus.PROCEED, next_phase=4)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 3 (Analyst) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """위험 목록 작성 확인"""
        risks = output.get("risks", [])
        critiques = output.get("critiques", [])

        total_issues = len(risks) + len(critiques)

        if total_issues > 0:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=5,
                reason=f"위험 {len(risks)}건, 결함 {len(critiques)}건 발견. 파수꾼에게 RULES 검증을 맡기라.",
                data={"risks": risks, "critiques": critiques}
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=4,
                reason="위험이 하나도 없다고? 다시 검토하라. 모든 것에는 위험이 있다."
            )

    def check_thinking(self, thinking: str) -> bool:
        """사고 과정에서 금지 패턴 감지"""
        for pattern in self.forbidden_patterns:
            if pattern in thinking:
                return False  # BLOCK - 해결책 제시 감지
        return True

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
