#!/usr/bin/env python3
"""
Phase 8: LeftState(좌의정) - 내정 검토

트리거: Phase 7 완료 후
허용: 이조/호조/예조 내정 심사
금지: 외정 검토, 실행, 최종 승인
관할: 이조(인사), 호조(재정), 예조(예법/문서)
"""

from .base import PhaseHook, PhaseResult, PhaseStatus


class Phase08LeftState(PhaseHook):
    """
    Phase 8: LeftState(좌의정) - 내정 검토

    역할: 내정(인사/재정/예법) 관점에서 설계를 심사
    페르소나: 신중한 내정 총괄, 안정 중시
    말투: "인사 관점에서", "재정 측면에서", "예법에 따르면"
    관할 육조: 이조(吏曹), 호조(戶曹), 예조(禮曹)
    """

    phase_number = 8
    role_name = "left-state-councilor"
    enforcement_message = "내정은 흐림 없이 명확해야 한다."

    # 강제 주입 메시지
    enforcement_message = "대충 처리한 건 이미 다 보인다."

    allowed_actions = [
        "review_personnel",     # 이조: 인사/역할 검토
        "review_finance",       # 호조: 재정/자원 검토
        "review_rites",         # 예조: 예법/문서 검토
        "assess_stability",     # 안정성 평가
        "check_governance",     # 거버넌스 확인
    ]

    forbidden_actions = [
        "review_external",      # 외정 검토 금지 (RightState 영역)
        "review_military",      # 병조 검토 금지
        "execute",              # 실행 금지
        "final_approve",        # 최종 승인 금지 (Sage 영역)
    ]

    # 육조별 검토 항목
    ministries = {
        "이조": ["역할 할당", "권한 설정", "스킬 관리"],
        "호조": ["리소스 예산", "토큰 관리", "비용 분석"],
        "예조": ["문서 형식", "학술 자문", "세션 관리"],
    }

    def validate_input(self, session_state: dict) -> PhaseResult:
        """Phase 7 완료 확인"""
        if session_state.get("phase_completed", {}).get(7, False):
            return PhaseResult(status=PhaseStatus.PROCEED, next_phase=8)
        return PhaseResult(
            status=PhaseStatus.BLOCK,
            next_phase=None,
            reason="Phase 7 (Architect) 미완료"
        )

    def validate_output(self, output: dict) -> PhaseResult:
        """내정 심사 완료 확인"""
        reviews = output.get("reviews", {})

        # 세 육조 검토 확인
        ijo = reviews.get("이조", {})
        hojo = reviews.get("호조", {})
        yejo = reviews.get("예조", {})

        all_reviewed = all([
            ijo.get("reviewed", False),
            hojo.get("reviewed", False),
            yejo.get("reviewed", False)
        ])

        if all_reviewed:
            issues = []
            for ministry, review in reviews.items():
                if review.get("issues"):
                    issues.extend(review["issues"])

            return PhaseResult(
                status=PhaseStatus.PROCEED,
                next_phase=9,
                reason=f"내정 심사 완료. 이슈 {len(issues)}건. 우의정에게 실무 심사를 맡기라.",
                data={"reviews": reviews, "issues": issues}
            )
        else:
            missing = []
            if not ijo.get("reviewed"):
                missing.append("이조")
            if not hojo.get("reviewed"):
                missing.append("호조")
            if not yejo.get("reviewed"):
                missing.append("예조")
            return PhaseResult(
                status=PhaseStatus.RETRY,
                next_phase=8,
                reason=f"미심사: {', '.join(missing)}. 내정 전체를 심사하라."
            )

    def check_scope(self, action: str, tool: str) -> bool:
        """역할 범위 내 행동인지 확인"""
        if action in self.forbidden_actions:
            return False
        # 실행 도구 금지
        if tool in ["Write", "Edit", "Bash"]:
            return False
        return True
