#!/usr/bin/env python3
"""
Phase 13: Validator(검증관) - 검증

트리거: Phase 12 완료 후
허용: 스키마/품질 검증, PASS/FAIL 판정
금지: 수정, 설계, 실행, 승인
완료 조건: PASS 또는 FAIL 판정
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase13Validator(PhaseHook):
    """
    Phase 13: Validator(검증관) - 검증

    역할: 품질 기준에 따라 PASS/FAIL 판정
    페르소나: 엄격한 품질 검증관
    말투: "PASS", "FAIL", "검증 결과"

    FAIL 시 Phase 11 (Executor)로 돌아감
    """

    phase_number = 13
    role_name = "validator"
    enforcement_message = "대충 끝낸 흔적이 그대로 남아 있다."

    # 강제 주입 메시지
    enforcement_message = "이 정도면 실무에서 바로 컷이다."

    allowed_actions = [
        "validate",             # 검증
        "check_schema",         # 스키마 확인
        "check_quality",        # 품질 확인
        "pass_judgment",        # PASS 판정
        "fail_judgment",        # FAIL 판정
        "run_tests",            # 테스트 실행
    ]

    forbidden_actions = [
        "modify",               # 수정 금지
        "fix",                  # 수정 금지
        "design",               # 설계 금지
        "execute",              # 실행 금지 (테스트 실행만 가능)
        "approve",              # 승인 금지 (Sage 영역)
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 12 완료 확인"""
        if session_state.get("phase_completed", {}).get(12, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=13)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 12 (Inspector) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """PASS/FAIL 판정 확인"""
        judgment = output.get("judgment")
        test_results = output.get("test_results", {})
        quality_score = output.get("quality_score")
        issues = output.get("issues", [])

        if judgment == "PASS":
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=14,
                reason="검증 PASS. 영의정에게 최종 결재를 구하라.",
                data={
                    "test_results": test_results,
                    "quality_score": quality_score
                }
            )
        elif judgment == "FAIL":
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=11,  # Executor로 돌아감
                reason=f"검증 FAIL. 이슈: {issues}. 실행관에게 재구현을 지시하라.",
                data={"issues": issues}
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=13,
                reason="판정이 없다. PASS 또는 FAIL을 명확히 하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 수정 도구 금지
        if tool in ["Write", "Edit"]:
            return False
        # Bash는 테스트 실행용으로 제한적 허용
        if tool == "Bash":
            return True  # 테스트 실행만
        # 조회 도구 허용
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return False
