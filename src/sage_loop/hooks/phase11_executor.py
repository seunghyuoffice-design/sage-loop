#!/usr/bin/env python3
"""
Phase 11: Executor(실행관) - 구현

트리거: Phase 10 승인 후
허용: 도구 호출, 코드 작성, 구현
금지: 설계 변경, 판단, 스킵, 승인
완료 조건: 설계대로 구현 완료
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase11Executor(PhaseHook):
    """
    Phase 11: Executor(실행관) - 구현

    역할: Architect의 설계를 그대로 구현한다.
    페르소나: 묵묵한 실행자, 판단 없이 실행
    말투: 없음 (코드로 말한다)

    중요: 설계를 변경하거나 판단하지 않는다.
    """

    phase_number = 11
    role_name = "executor"
    enforcement_message = "실행 가능한 코드만 제출해라. TODO, 생략은 허용되지 않는다."

    # 강제 주입 메시지
    enforcement_message = "끝까지 책임질 생각 없으면 시작하지 마라."

    allowed_actions = [
        "implement",            # 구현
        "write_code",           # 코드 작성
        "call_tool",            # 도구 호출
        "create_file",          # 파일 생성
        "edit_file",            # 파일 수정
        "run_command",          # 명령 실행
    ]

    forbidden_actions = [
        "modify_design",        # 설계 변경 금지
        "judge",                # 판단 금지
        "skip",                 # 스킵 금지
        "approve",              # 승인 금지
        "evaluate",             # 평가 금지 (Validator 영역)
        "simplify",             # 단순화 금지 (설계대로)
    ]

    # 금지 사고 패턴 (판단/스킵)
    forbidden_patterns = [
        "간단해서",
        "이건 스킵",
        "굳이 안 해도",
        "불필요한",
        "나중에",
        "이건 생략",
        "이 정도면",
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 10 승인 확인"""
        phase10_output = session_state.get("phase_outputs", {}).get(10, {})
        decision = phase10_output.get("decision")

        if decision in ["APPROVED", "CONDITIONAL"]:
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=11)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 10 (Sage) 승인 필요"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """구현 완료 확인"""
        implemented = output.get("implemented", False)
        files_created = output.get("files_created", [])
        files_modified = output.get("files_modified", [])
        commands_run = output.get("commands_run", [])

        has_work = implemented or files_created or files_modified or commands_run

        if has_work and implemented:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=12,
                reason="구현 완료. 감찰관에게 감찰을 맡기라.",
                data={
                    "files_created": files_created,
                    "files_modified": files_modified,
                    "commands_run": commands_run
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=11,
                reason="구현이 완료되지 않았다. 설계대로 구현하라."
            )

    def check_thinking(self, thinking: str) -> bool:
        """사고 과정에서 금지 패턴 감지"""
        for pattern in self.forbidden_patterns:
            if pattern in thinking:
                return False  # BLOCK - 스킵/판단 시도 감지
        return True

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 허용 (Executor만!)
        if tool in ["Write", "Edit", "Bash", "TodoWrite"]:
            return True
        # 조회 도구도 허용 (구현 중 참조용)
        if tool in ["Read", "Glob", "Grep"]:
            return True
        return True
