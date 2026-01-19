"""
Branch Handler - 동적 분기 처리

분기 규칙:
    - analyst → feasibility-checker (실현 가능성 불확실)
    - critic → constraint-enforcer (제약 위반 가능성)

분기 제한:
    - 역할별 최대 루프 횟수 (기본: 3회)
    - 세션별 총 분기 횟수 (기본: 5회)
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..config import get_settings
from ..schemas import RoleOutput
from ..services.state_service import StateService

logger = logging.getLogger(__name__)


@dataclass
class BranchRule:
    """분기 규칙"""

    from_role: str
    to_role: str
    condition: str
    max_loops: int = 3


@dataclass
class BranchDecision:
    """분기 결정 결과"""

    action: str  # proceed, branch, escalate
    target_role: Optional[str] = None
    reason: Optional[str] = None


# 기본 분기 규칙 (config.yaml에서 로드 가능)
DEFAULT_BRANCH_RULES = [
    BranchRule(
        from_role="analyst",
        to_role="feasibility-checker",
        condition="feasibility_uncertain",
        max_loops=3,
    ),
    BranchRule(
        from_role="critic",
        to_role="constraint-enforcer",
        condition="constraint_violation",
        max_loops=2,
    ),
]


class BranchHandler:
    """분기 처리기"""

    def __init__(self, state_service: StateService, rules: Optional[list[BranchRule]] = None):
        self.state_service = state_service
        self.rules = rules or DEFAULT_BRANCH_RULES
        self._rules_by_role = {rule.from_role: rule for rule in self.rules}

    async def evaluate(
        self,
        session_id: str,
        role: str,
        output: RoleOutput,
    ) -> BranchDecision:
        """
        분기 조건 평가

        Args:
            session_id: 세션 ID
            role: 현재 역할
            output: 역할 출력

        Returns:
            BranchDecision: 분기 결정 (proceed, branch, escalate)
        """
        rule = self._rules_by_role.get(role)
        if not rule:
            return BranchDecision(action="proceed")

        # 조건 평가
        should_branch = await self._evaluate_condition(rule.condition, output)

        if not should_branch:
            return BranchDecision(action="proceed")

        # 루프 카운트 확인
        loop_count = await self.state_service.get_loop_count(session_id, role)

        if loop_count >= rule.max_loops:
            logger.warning(f"[{session_id}] Max loops exceeded for {role}: {loop_count}/{rule.max_loops}")
            return BranchDecision(
                action="escalate",
                reason=f"최대 분기 횟수 초과 ({loop_count}/{rule.max_loops})",
            )

        # 총 분기 횟수 확인
        settings = get_settings()
        session = await self.state_service.get_session(session_id)
        if session and session.branch_count >= settings.chain.max_total_branches:
            logger.warning(f"[{session_id}] Max total branches exceeded: {session.branch_count}")
            return BranchDecision(
                action="escalate",
                reason=f"총 분기 횟수 초과 ({session.branch_count}/{settings.chain.max_total_branches})",
            )

        # 분기 결정
        await self.state_service.increment_loop_count(session_id, role)
        await self.state_service.increment_branch_count(session_id)

        logger.info(f"[{session_id}] Branch: {role} → {rule.to_role}")

        return BranchDecision(
            action="branch",
            target_role=rule.to_role,
            reason=f"조건 충족: {rule.condition}",
        )

    async def _evaluate_condition(self, condition: str, output: RoleOutput) -> bool:
        """
        분기 조건 평가

        조건 종류:
        - feasibility_uncertain: 실현 가능성 불확실
        - constraint_violation: 제약 위반 가능성
        """
        if not output.output:
            return False

        data = output.output

        if condition == "feasibility_uncertain":
            # Analyst 출력에서 불확실성 감지
            # 실제 구현 시: 선별된 아이디어 중 "불확실", "검토 필요" 키워드 탐지
            selected = data.get("selected", [])
            for item in selected:
                reason = item.get("reason", "").lower()
                if any(kw in reason for kw in ["불확실", "검토", "확인 필요"]):
                    return True
            return False

        elif condition == "constraint_violation":
            # Critic 출력에서 위반 가능성 감지
            # 실제 구현 시: 위험 분석에서 "위반", "금지", "제약" 키워드 탐지
            risk_analysis = data.get("risk_analysis", [])
            for item in risk_analysis:
                for field in ["logical_flaws", "reality_issues", "hidden_costs"]:
                    value = item.get(field, "").lower()
                    if any(kw in value for kw in ["위반", "금지", "제약", "license", "gpl"]):
                        return True
            return False

        return False

    def get_branch_target(self, role: str) -> Optional[str]:
        """역할의 분기 대상 조회"""
        rule = self._rules_by_role.get(role)
        return rule.to_role if rule else None

    def get_return_role(self, branch_role: str) -> Optional[str]:
        """분기 역할의 복귀 대상 조회"""
        for rule in self.rules:
            if rule.to_role == branch_role:
                return rule.from_role
        return None


def load_branch_rules_from_config(config: dict) -> list[BranchRule]:
    """config.yaml에서 분기 규칙 로드"""
    rules = []

    chains = config.get("chains", {})
    for chain_name, chain_def in chains.items():
        branches = chain_def.get("branches", [])
        for branch in branches:
            rules.append(
                BranchRule(
                    from_role=branch["from"],
                    to_role=branch["to"],
                    condition=branch["condition"],
                    max_loops=branch.get("max_loops", 3),
                )
            )

    return rules
