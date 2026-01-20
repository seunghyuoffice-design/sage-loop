#!/usr/bin/env python3
"""
Phase 5: Censor(파수꾼) - RULES 사전 봉쇄

트리거: Phase 4 완료 후
허용: RULES 대조, PASS/BLOCK 판정
금지: 설계, 구현, 품질 평가, 문서 수정
완료 조건: PASS 또는 BLOCK 판정
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase05Censor(PhaseHook):
    """
    Phase 5: Censor(파수꾼) - RULES 사전 봉쇄

    역할: CLAUDE.md RULES만 대조하여 PASS/BLOCK 판정
    페르소나: 냉정한 법관, 규칙 문자 그대로 해석
    말투: "RULES 위반", "PASS", "BLOCK", "허용", "금지"
    """

    phase_number = 5
    role_name = "censor"

    allowed_actions = [
        "check_rules",          # RULES 대조
        "pass_judgment",        # PASS 판정
        "block_judgment",       # BLOCK 판정
        "cite_rule",            # 규칙 인용
    ]

    forbidden_actions = [
        "design",               # 설계 금지
        "execute",              # 구현 금지
        "evaluate_quality",     # 품질 평가 금지 (Validator 영역)
        "modify_document",      # 문서 수정 금지
        "suggest",              # 제안 금지
        "improve",              # 개선 금지
    ]

    # RULES 위반 키워드 (CLAUDE.md 기준)
    rules_violations = {
        "LICENSE": ["GPL", "LGPL", "AGPL"],
        "DATA": ["OpenAI", "Claude API", "외부 API"],
        "ACCESS": ["ssh core"],  # 직접 접근 금지
        "EXEC": ["rovers 로컬 실행"],
    }

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 4 완료 확인"""
        if session_state.get("phase_completed", {}).get(4, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=5)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 4 (Critic) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """PASS/BLOCK 판정 확인"""
        judgment = output.get("judgment")
        violations = output.get("violations", [])

        if judgment == "PASS":
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=6,
                reason="RULES 위반 없음. PASS. 대제학에게 학술 자문을 구하라."
            )
        elif judgment == "BLOCK":
            return PhaseResult(
                status=PhaseStatus.BLOCK,
                next_phase=None,
                reason=f"RULES 위반. BLOCK. 위반 사항: {violations}"
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=5,
                reason="판정이 없다. PASS 또는 BLOCK을 명확히 하라."
            )

    def check_for_violations(self, content: str) -> list:
        """RULES 위반 키워드 검사"""
        found = []
        for rule, keywords in self.rules_violations.items():
            for keyword in keywords:
                if keyword in content:
                    found.append(f"{rule}: {keyword}")
        return found

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 수정 도구 금지
        if tool in ["Write", "Edit"]:
            return False
        # Read만 허용 (RULES 확인용)
        if tool in ["Read", "Grep"]:
            return True
        return False
