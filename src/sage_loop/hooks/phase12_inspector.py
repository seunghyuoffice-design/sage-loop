#!/usr/bin/env python3
"""
Phase 12: Inspector(감찰관) - 감찰

트리거: Phase 11 완료 후
허용: 구현 결과 감찰, 누락 확인
금지: 수정, 설계, 승인, 판정
완료 조건: 감찰 보고서 작성됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase12Inspector(PhaseHook):
    """
    Phase 12: Inspector(감찰관) - 감찰

    역할: 구현 결과가 설계대로인지 감찰한다.
    페르소나: 꼼꼼한 감찰관, 체크리스트 중시
    말투: "확인 결과", "누락 발견", "설계와 일치/불일치"

    수정하지 않는다. 발견만 한다.
    """

    phase_number = 12
    role_name = "inspector"
    enforcement_message = "이미 다 봤다. 어디서 밀도 떨어졌는지도 알고 있다."

    allowed_actions = [
        "inspect",              # 감찰
        "check_implementation", # 구현 확인
        "find_missing",         # 누락 찾기
        "compare_to_design",    # 설계와 비교
        "report",               # 보고
    ]

    forbidden_actions = [
        "modify",               # 수정 금지
        "fix",                  # 수정 금지
        "design",               # 설계 금지
        "approve",              # 승인 금지
        "judge",                # 판정 금지 (Validator 영역)
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 11 완료 확인"""
        if session_state.get("phase_completed", {}).get(11, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=12)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 11 (Executor) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """감찰 보고서 확인"""
        inspection_report = output.get("inspection_report", {})
        findings = output.get("findings", [])
        missing_items = output.get("missing_items", [])
        matches_design = output.get("matches_design", None)

        has_report = inspection_report or findings is not None or matches_design is not None

        if has_report:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=13,
                reason=f"감찰 완료. 발견 {len(findings)}건, 누락 {len(missing_items)}건. 검증관에게 검증을 맡기라.",
                data={
                    "inspection_report": inspection_report,
                    "findings": findings,
                    "missing_items": missing_items,
                    "matches_design": matches_design
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=12,
                reason="감찰 보고서가 없다. 구현 결과를 감찰하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 수정 도구 금지 (감찰만, 수정 안 함)
        if tool in ["Write", "Edit", "Bash"]:
            return False
        # 조회 도구만 허용
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return False
