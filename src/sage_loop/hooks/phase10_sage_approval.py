#!/usr/bin/env python3
"""
Phase 10: Sage(허가) - 영의정 실행 허가

트리거: Phase 9 완료 후
허용: 승인/거부 판정
금지: 직접 실행, 설계 수정
특수: 거부 시 Phase 1 재시작 (최대 3회)
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


MAX_RETRY_COUNT = 3


class Phase10SageApproval(PhaseHook):
    """
    Phase 10: Sage(허가) - 영의정 실행 허가

    역할: 실행 허가 또는 거부
    페르소나: 신중하고 권위 있는 영의정
    말투:
      - 승인: "가하다. 시행하라."
      - 거부: "불가하다. [사유]. 다시 검토하라."
      - 조건부: "조건을 충족하면 가하다."
    """

    phase_number = 10
    role_name = "sage"

    allowed_actions = [
        "approve",              # 승인
        "reject",               # 거부
        "conditional_approve",  # 조건부 승인
    ]

    forbidden_actions = [
        "execute",              # 직접 실행 금지
        "modify_design",        # 설계 수정 금지
        "validate",             # 검증 금지 (Validator 영역)
        "implement",            # 구현 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 9 (RightState) 완료 확인"""
        if session_state.get("phase_completed", {}).get(9, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=10)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 9 (RightState) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """Sage 판정 처리"""
        decision = output.get("decision")
        retry_count = output.get("retry_count", 0)
        reason = output.get("reason", "")

        if decision == "APPROVED":
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=11,
                reason="가하다. 시행하라."
            )

        elif decision == "CONDITIONAL":
            conditions = output.get("conditions", [])
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=11,
                reason=f"조건부 승인. 조건: {conditions}",
                data={"conditions": conditions}
            )

        elif decision == "REJECTED":
            if retry_count < MAX_RETRY_COUNT:
                return PhaseResult(
                    status=PhaseStatus.RESTART,
                    next_phase=1,  # Phase 1부터 재시작
                    retry_count=retry_count + 1,
                    reason=f"불가하다. {reason}. 다시 검토하라. (재시도 {retry_count + 1}/{MAX_RETRY_COUNT})"
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
                next_phase=10,
                reason="판정이 필요하다. APPROVED/CONDITIONAL/REJECTED 중 하나를 선택하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
