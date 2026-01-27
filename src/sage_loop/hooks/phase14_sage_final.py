#!/usr/bin/env python3
"""
Phase 14: Sage(결재) - 영의정 최종 결재

트리거: Phase 13 PASS 후
허용: 최종 승인/거부
금지: 직접 수정, 재실행
특수: 거부 시 Phase 1 재시작 (최대 3회, Phase 10과 공유)
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


MAX_RETRY_COUNT = 3


class Phase14SageFinal(PhaseHook):
    """
    Phase 14: Sage(결재) - 영의정 최종 결재

    역할: 최종 결재
    페르소나: 신중하고 권위 있는 영의정
    말투:
      - 승인: "완료를 확인하다. 기록하라."
      - 거부: "불가하다. [사유]. 처음부터 다시 검토하라."

    Phase 10과 재시도 횟수 공유 (총 3회)
    """

    phase_number = 14
    role_name = "sage"
    enforcement_message = "최종 결재에서 빠진 건 없는가?"

    allowed_actions = [
        "final_approve",        # 최종 승인
        "final_reject",         # 최종 거부
    ]

    forbidden_actions = [
        "modify",               # 직접 수정 금지
        "re_execute",           # 재실행 금지
        "design",               # 설계 금지
        "implement",            # 구현 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 13 PASS 판정 확인"""
        phase13_output = session_state.get("phase_outputs", {}).get(13, {})
        if phase13_output.get("judgment") == "PASS":
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=14)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=11,  # Executor로 돌아감
            reason="Phase 13 (Validator) PASS 판정 필요"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """최종 결재 처리"""
        decision = output.get("decision")
        total_retry_count = output.get("total_retry_count", 0)  # Phase 10과 공유
        reason = output.get("reason", "")

        if decision == "APPROVED":
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=15,
                reason="완료를 확인하다. 역사관에게 기록을 맡기라."
            )

        elif decision == "REJECTED":
            if total_retry_count < MAX_RETRY_COUNT:
                return PhaseResult(
                    status=PhaseStatus.RESTART,
                    next_phase=1,  # Phase 1부터 재시작
                    retry_count=total_retry_count + 1,
                    reason=f"불가하다. {reason}. 처음부터 다시 검토하라. (재시도 {total_retry_count + 1}/{MAX_RETRY_COUNT})"
                )
            else:
                return PhaseResult(
                    status=PhaseStatus.ABORT,
                    next_phase=None,
                    reason=f"최대 재시도 횟수 {MAX_RETRY_COUNT}회 초과. 작업을 중단하라."
                )

        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=14,
                reason="최종 판정이 필요하다. APPROVED 또는 REJECTED를 선택하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 모든 수정/실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
