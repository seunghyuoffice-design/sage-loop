#!/usr/bin/env python3
"""
Phase 1: Sage(접수) - 영의정 안건 접수

트리거: UserPromptSubmit
허용: 안건 분류, TodoWrite 지시
금지: 체인 선택, 직접 분석, 직접 실행
완료 조건: TodoWrite로 태스크 작성됨
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase01SageIntake(PhaseHook):
    """
    Phase 1: Sage(접수) - 영의정 안건 접수

    역할: 안건을 접수하고 검토를 지시한다.
    페르소나: 신중하고 권위 있는 영의정
    말투: "검토하라."
    """

    phase_number = 1
    role_name = "sage"
    enforcement_message = "접수 내용이 불명확하면 진행 불가다."

    # 강제 주입 메시지
    enforcement_message = "끝까지 책임질 생각 없으면 시작하지 마라."

    allowed_actions = [
        "classify_petition",    # 안건 분류
        "assign_review",        # 검토 지시
        "todowrite_trigger",    # TodoWrite 트리거
    ]

    forbidden_actions = [
        "select_chain",         # 체인 선택 금지
        "analyze",              # 직접 분석 금지
        "execute",              # 직접 실행 금지
        "judge",                # 판단 금지
        "ideate",               # 아이디어 발산 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """안건이 존재하는지 확인"""
        petition = session_state.get("petition")
        if not petition:
            return PhaseResult(
                status=PhaseStatus.BLOCK,
                next_phase=None,
                reason="안건이 없습니다. 요청을 명확히 하라."
            )
        return PhaseResult(status=PhaseStatus.PROCEED, next_phase=1)

    def validate_output(self, output: dict) -> PhaseResult:
        """TodoWrite 완료 확인"""
        todos = output.get("todos", [])

        if len(todos) > 0 and all(t.get("content") for t in todos):
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=2,
                reason="검토하라. 현인에게 아이디어를 구하라."
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=1,
                reason="태스크가 명확하지 않다. TodoWrite로 작성하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        # TodoWrite만 허용
        if tool == "TodoWrite":
            return True
        # Read, Glob, Grep은 허용 (안건 파악용)
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return False
