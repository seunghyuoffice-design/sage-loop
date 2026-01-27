#!/usr/bin/env python3
"""
Phase 6: Academy(대제학) - 학술 자문

트리거: Phase 5 완료 후 (PASS 판정)
허용: 학술 자문, 근거/선례 제공, RULES 해석
금지: 판단, 설계, 실행, 승인
완료 조건: 근거/선례 제공됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase06Academy(PhaseHook):
    """
    Phase 6: Academy(대제학) - 학술 자문

    역할: 학술적 근거와 선례를 제공한다.
    페르소나: 박식한 학자, 역사와 선례 인용
    말투: "선례에 따르면", "근거는", "참고할 만한 것은"
    """

    phase_number = 6
    role_name = "academy"
    enforcement_message = "근거 없는 해석은 학술 자문이 아니다."

    allowed_actions = [
        "provide_reference",    # 참고 자료 제공
        "cite_precedent",       # 선례 인용
        "interpret_rules",      # RULES 해석
        "explain_context",      # 맥락 설명
        "suggest_reading",      # 읽을거리 제안
    ]

    forbidden_actions = [
        "judge",                # 판단 금지
        "design",               # 설계 금지 (Architect 영역)
        "execute",              # 실행 금지
        "approve",              # 승인 금지 (Sage 영역)
        "decide",               # 결정 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 5 PASS 판정 확인"""
        phase5_output = session_state.get("phase_outputs", {}).get(5, {})
        if phase5_output.get("judgment") == "PASS":
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=6)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 5 (Censor) PASS 판정 필요"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """근거/선례 제공 확인"""
        references = output.get("references", [])
        precedents = output.get("precedents", [])
        interpretation = output.get("interpretation", "")

        has_content = len(references) > 0 or len(precedents) > 0 or interpretation

        if has_content:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=7,
                reason="학술 자문 완료. 장인에게 설계를 맡기라.",
                data={
                    "references": references,
                    "precedents": precedents,
                    "interpretation": interpretation
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=6,
                reason="근거나 선례가 제공되지 않았다. 학술적 자문을 제공하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        # 조회 도구만 허용
        if tool in ["Read", "Glob", "Grep", "WebSearch", "WebFetch"]:
            return True
        return False
