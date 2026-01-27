#!/usr/bin/env python3
"""
Phase 9: RightState(우의정) - 실무/외정 검토

트리거: Phase 8 완료 후
허용: 병조/형조/공조 실무 심사
금지: 내정 검토, 실행, 최종 승인
관할: 병조(실행), 형조(검증), 공조(인프라)
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase09RightState(PhaseHook):
    """
    Phase 9: RightState(우의정) - 실무/외정 검토

    역할: 실무(실행/검증/인프라) 관점에서 설계를 심사
    페르소나: 실용적인 실무 총괄, 효율 중시
    말투: "실행 관점에서", "보안 측면에서", "인프라 상으로"
    관할 육조: 병조(兵曹), 형조(刑曹), 공조(工曹)
    """

    phase_number = 9
    role_name = "right-state-councilor"
    enforcement_message = "실무 검토에서 빠진 건 없는가?"

    allowed_actions = [
        "review_military",      # 병조: 실행/배포 검토
        "review_justice",       # 형조: 검증/감사 검토
        "review_works",         # 공조: 인프라/빌드 검토
        "assess_feasibility",   # 실현가능성 평가
        "check_security",       # 보안 확인
    ]

    forbidden_actions = [
        "review_internal",      # 내정 검토 금지 (LeftState 영역)
        "review_personnel",     # 이조 검토 금지
        "execute",              # 실행 금지
        "final_approve",        # 최종 승인 금지 (Sage 영역)
    ]

    # 육조별 검토 항목
    ministries = {
        "병조": ["배포 계획", "파이프라인", "실행 순서"],
        "형조": ["컴플라이언스", "감사", "검증 계획"],
        "공조": ["인프라", "빌드", "환경 설정"],
    }

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 8 완료 확인"""
        if session_state.get("phase_completed", {}).get(8, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=9)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 8 (LeftState) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """실무 심사 완료 확인"""
        reviews = output.get("reviews", {})

        # 세 육조 검토 확인
        byeongjo = reviews.get("병조", {})
        hyeongjo = reviews.get("형조", {})
        gongjo = reviews.get("공조", {})

        all_reviewed = all([
            byeongjo.get("reviewed", False),
            hyeongjo.get("reviewed", False),
            gongjo.get("reviewed", False)
        ])

        if all_reviewed:
            issues = []
            for ministry, review in reviews.items():
                if review.get("issues"):
                    issues.extend(review["issues"])

            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=10,
                reason=f"실무 심사 완료. 이슈 {len(issues)}건. 영의정에게 실행 허가를 구하라.",
                data={"reviews": reviews, "issues": issues}
            )
        else:
            missing = []
            if not byeongjo.get("reviewed"):
                missing.append("병조")
            if not hyeongjo.get("reviewed"):
                missing.append("형조")
            if not gongjo.get("reviewed"):
                missing.append("공조")
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=9,
                reason=f"미심사: {', '.join(missing)}. 실무 전체를 심사하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
