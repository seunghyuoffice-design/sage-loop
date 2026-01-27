#!/usr/bin/env python3
"""
Phase 15: Historian(역사관) - 기록

트리거: Phase 14 승인 후
허용: 기록, 변경 이력 저장
금지: 판단, 수정, 승인, 실행
완료 조건: 기록 완료
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase15Historian(PhaseHook):
    """
    Phase 15: Historian(역사관) - 기록

    역할: 변경 이력을 기록한다.
    페르소나: 묵묵한 기록자, 사실만 기록
    말투: "기록함", "변경 이력", "시각"

    판단하지 않는다. 기록만 한다.
    """

    phase_number = 15
    role_name = "historian"
    enforcement_message = "기록에 빠진 건 없는가? 누락은 곧 왜곡이다."

    allowed_actions = [
        "record",               # 기록
        "log_changes",          # 변경 이력 기록
        "save_history",         # 히스토리 저장
        "timestamp",            # 타임스탬프
        "archive",              # 아카이브
    ]

    forbidden_actions = [
        "judge",                # 판단 금지
        "modify",               # 수정 금지
        "approve",              # 승인 금지
        "execute",              # 실행 금지
        "evaluate",             # 평가 금지
    ]

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 14 승인 확인"""
        phase14_output = session_state.get("phase_outputs", {}).get(14, {})
        if phase14_output.get("decision") == "APPROVED":
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=15)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 14 (Sage 결재) 승인 필요"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """기록 완료 확인"""
        recorded = output.get("recorded", False)
        history = output.get("history", {})
        changelog = output.get("changelog", [])

        has_record = recorded or history or changelog

        if has_record:
            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=16,
                reason="기록 완료. 회고관에게 회고를 맡기라.",
                data={
                    "history": history,
                    "changelog": changelog
                }
            )
        else:
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=15,
                reason="기록이 없다. 변경 이력을 기록하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 기록용 Write만 허용 (히스토리 파일)
        if tool == "Write":
            return True  # 히스토리 파일 작성만
        # 조회 도구 허용
        if tool in ["Read", "Glob", "Grep"]:
            return True
        # Bash는 git log 등 조회용으로 제한
        if tool == "Bash":
            return True  # git log, git diff 등
        return False
