#!/usr/bin/env python3
"""
Phase 17: Improver(개선관) - 개선

트리거: Phase 16 완료 후
허용: 개선점 제안, 다음 작업 연결
금지: 직접 실행, 현 작업 수정
완료 조건: 개선점 제안됨 → END
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase17Improver(PhaseHook):
    """
    Phase 17: Improver(개선관) - 개선

    역할: 개선점을 제안하고 다음 작업으로 연결한다.
    페르소나: 미래 지향적 개선자
    말투: "개선점", "다음에는", "제안"

    직접 실행하지 않는다. 제안만 한다.
    이 Phase가 끝나면 Sage Loop 종료.
    """

    phase_number = 17
    role_name = "improver"
    enforcement_message = "개선안은 구체적이어야 한다. 추상적 제안은 기각."

    # 강제 주입 메시지
    enforcement_message = "표면만 건드린 건 개선이 아니라 회피다."

    allowed_actions = [
        "suggest_improvements", # 개선점 제안
        "propose_next",         # 다음 작업 제안
        "identify_gaps",        # 갭 식별
        "recommend",            # 권고
        "plan_future",          # 미래 계획
    ]

    forbidden_actions = [
        "execute",              # 직접 실행 금지
        "modify_current",       # 현 작업 수정 금지
        "implement",            # 구현 금지
        "fix",                  # 수정 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 16 완료 확인"""
        if session_state.get("phase_completed", {}).get(16, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=17)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 16 (Reflector) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """개선점 제안 확인 → END"""
        improvements = output.get("improvements", [])
        next_tasks = output.get("next_tasks", [])
        recommendations = output.get("recommendations", [])

        has_suggestions = improvements or next_tasks or recommendations

        if has_suggestions:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=None,  # END - Sage Loop 종료
                reason="개선점 제안 완료. Sage Loop 종료.",
                data={
                    "improvements": improvements,
                    "next_tasks": next_tasks,
                    "recommendations": recommendations,
                    "exit_signal": True
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=17,
                reason="개선점이 없다. 개선점을 제안하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        # 조회 도구만 허용
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return False
