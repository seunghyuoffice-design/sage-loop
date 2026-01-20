#!/usr/bin/env python3
"""
Phase 7: Architect(장인) - 설계

트리거: Phase 6 완료 후
허용: 설계, 구조 정의, blueprint 출력
금지: 구현, 검증, 승인, 실행
완료 조건: 설계 문서/blueprint 작성됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase07Architect(PhaseHook):
    """
    Phase 7: Architect(장인) - 설계

    역할: 구조를 설계하고 blueprint를 출력한다.
    페르소나: 꼼꼼한 건축가, 구조 중심 사고
    말투: "구조는", "설계는", "인터페이스는", "흐름은"
    """

    phase_number = 7
    role_name = "architect"

    allowed_actions = [
        "design",               # 설계
        "define_structure",     # 구조 정의
        "create_blueprint",     # blueprint 생성
        "define_interface",     # 인터페이스 정의
        "plan_flow",            # 흐름 계획
    ]

    forbidden_actions = [
        "implement",            # 구현 금지 (Executor 영역)
        "validate",             # 검증 금지 (Validator 영역)
        "approve",              # 승인 금지 (Sage 영역)
        "execute",              # 실행 금지
        "write_code",           # 코드 작성 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 6 완료 확인"""
        if session_state.get("phase_completed", {}).get(6, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=7)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 6 (Academy) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """설계 문서/blueprint 작성 확인"""
        blueprint = output.get("blueprint")
        design = output.get("design")
        structure = output.get("structure")

        has_design = blueprint or design or structure

        if has_design:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=8,
                reason="설계 완료. 좌의정에게 내정 심사를 맡기라.",
                data={
                    "blueprint": blueprint,
                    "design": design,
                    "structure": structure
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=7,
                reason="설계가 없다. blueprint를 작성하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 코드 작성 도구 금지 (설계 문서만 가능)
        if tool in ["Edit", "Bash"]:
            return False
        # 설계 문서 작성은 Write로 허용
        if tool == "Write":
            return True  # 설계 문서만
        # 조회 도구 허용
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return False
