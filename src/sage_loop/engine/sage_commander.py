"""
Sage Commander - 지휘관 모드 핵심 로직

최소 컨텍스트(~5K 토큰)로 전체 체인을 지휘.
역할 실행은 Task로 위임하여 컨텍스트 격리.

지휘관 컨텍스트 내용:
    - 원본 요청 (1회)
    - 현재 체인 상태
    - 역할별 요약 (압축)
    - 다음 결정 정보

총 예상 크기: ~5K 토큰 (vs 기존 100K+)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..schemas import ChainType
from ..services.state_service import StateService
from .context_compactor import CompactedOutput, ContextCompactor
from .task_dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)


@dataclass
class CommanderState:
    """지휘관 상태 (최소 컨텍스트)"""

    session_id: str
    user_request: str  # 원본 요청 (1회만 저장)
    chain_type: ChainType
    current_role: Optional[str] = None
    completed_roles: list[str] = field(default_factory=list)
    summaries: dict[str, str] = field(default_factory=dict)  # 역할별 요약만
    branch_count: int = 0
    status: str = "pending"
    started_at: Optional[str] = None
    last_update: Optional[str] = None


@dataclass
class ChainResult:
    """체인 실행 결과"""

    session_id: str
    status: str  # completed, failed, waiting_approval
    final_summary: str
    completed_roles: list[str]
    branch_count: int
    error: Optional[str] = None


# 체인별 역할 정의 (CLAUDE.md SAGE_LOOP 기준)
CHAIN_ROLES = {
    ChainType.FULL: [
        "ideator",  # Phase 1: 아이디어 생성
        "analyst",  # Phase 2: 분석 및 선별
        "critic",  # Phase 3: 위험/결함 비판
        "censor",  # Phase 4: RULES 위반 사전 봉쇄
        "academy",  # Phase 5: 학술 자문/근거 제공
        "architect",  # Phase 6: 설계 수립
        "left-state-councilor",  # Phase 7: 내정 검토 (좌의정)
        "right-state-councilor",  # Phase 8: 실무 검토 (우의정)
        # Phase 9: Sage 자체가 오케스트레이터이므로 제외
        "executor",  # Phase 10: 설계 구현
        "inspector",  # Phase 11: 실행 결과 감찰
        "validator",  # Phase 12: 최종 검증
        "historian",  # Phase 13: 이력 기록
        "reflector",  # Phase 14: 회고 및 교훈
        "improver",  # Phase 15: 개선 사항 도출
    ],
    ChainType.QUICK: [
        "critic",
        "architect",
        "executor",
        "validator",
        "historian",
    ],
    ChainType.REVIEW: ["critic", "validator"],
    ChainType.DESIGN: ["ideator", "analyst", "critic", "architect"],
}

# 분기 조건 (역할 → 분기 대상)
BRANCH_CONDITIONS = {
    "analyst": {
        "condition": "feasibility_uncertain",
        "target": "feasibility-checker",
        "keywords": ["불확실", "검토 필요", "미정", "확인 필요"],
    },
    "critic": {
        "condition": "constraint_violation",
        "target": "constraint-enforcer",
        "keywords": ["위반", "금지", "license", "gpl", "보안"],
    },
    "censor": {
        "condition": "rules_violation",
        "target": "policy-keeper",
        "keywords": ["위반", "금지", "RULES", "정책"],
    },
    "inspector": {
        "condition": "quality_issue",
        "target": "validator",
        "keywords": ["품질", "미흡", "재검토", "문제"],
    },
}


class SageCommander:
    """Sage 지휘관 - 최소 컨텍스트로 체인 조율"""

    def __init__(self, state_service: Optional[StateService] = None):
        self.state_service = state_service or StateService()
        self.dispatcher = TaskDispatcher(self.state_service)
        self.compactor = ContextCompactor()

    async def execute_chain(
        self,
        session_id: str,
        user_request: str,
        chain_type: ChainType = ChainType.FULL,
    ) -> ChainResult:
        """
        체인 실행 (지휘관 모드)

        Sage 컨텍스트에는:
        - 원본 요청
        - 현재 상태
        - 역할별 요약 (압축된)
        - 다음 결정에 필요한 정보만

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청
            chain_type: 체인 타입

        Returns:
            ChainResult: 체인 실행 결과
        """
        logger.info(f"[{session_id}] SageCommander starting chain: {chain_type.value}")

        # 지휘관 상태 초기화
        state = CommanderState(
            session_id=session_id,
            user_request=user_request,
            chain_type=chain_type,
            started_at=datetime.now().isoformat(),
        )

        roles = CHAIN_ROLES.get(chain_type, CHAIN_ROLES[ChainType.FULL])
        previous_outputs: dict[str, CompactedOutput] = {}

        try:
            for role in roles:
                state.current_role = role
                state.last_update = datetime.now().isoformat()

                logger.info(f"[{session_id}] Executing role: {role}")

                # Task로 역할 실행 (컨텍스트 격리)
                result = await self.dispatcher.dispatch(
                    session_id=session_id,
                    role=role,
                    user_request=user_request,
                    previous_outputs=previous_outputs,
                )

                if result.status == "failed":
                    logger.error(f"[{session_id}] Role {role} failed: {result.error}")
                    return ChainResult(
                        session_id=session_id,
                        status="failed",
                        final_summary=f"{role} 실패: {result.error}",
                        completed_roles=state.completed_roles,
                        branch_count=state.branch_count,
                        error=result.error,
                    )

                # 요약만 저장 (전체는 Redis에)
                state.summaries[role] = result.summary
                state.completed_roles.append(role)

                # CompactedOutput 생성 (다음 역할 입력용)
                compacted = CompactedOutput(
                    role=role,
                    summary=result.summary,
                    key_points=[],
                    next_input_hint=self._get_next_hint(role),
                )
                previous_outputs[role] = compacted

                # 분기 평가 (요약 기반)
                should_branch, branch_target = self._evaluate_branch(role, result.summary)
                if should_branch and branch_target:
                    logger.info(f"[{session_id}] Branching to {branch_target}")
                    state.branch_count += 1

                    # 분기 역할 실행
                    branch_result = await self.dispatcher.dispatch(
                        session_id=session_id,
                        role=branch_target,
                        user_request=user_request,
                        previous_outputs=previous_outputs,
                    )

                    if branch_result.status == "completed":
                        state.summaries[branch_target] = branch_result.summary
                        previous_outputs[branch_target] = CompactedOutput(
                            role=branch_target,
                            summary=branch_result.summary,
                            key_points=[],
                            next_input_hint="",
                        )

                # 코칭 피드백 생성 (선택적)
                coaching = self._generate_coaching(role, result.summary)
                if coaching:
                    logger.debug(f"[{session_id}] Coaching for {role}: {coaching}")

            # 체인 완료
            state.status = "completed"
            final_summary = self._build_final_summary(state)

            logger.info(f"[{session_id}] Chain completed successfully")

            return ChainResult(
                session_id=session_id,
                status="completed",
                final_summary=final_summary,
                completed_roles=state.completed_roles,
                branch_count=state.branch_count,
            )

        except Exception as e:
            logger.error(f"[{session_id}] Chain execution error: {e}")
            return ChainResult(
                session_id=session_id,
                status="failed",
                final_summary=f"체인 실행 오류: {str(e)}",
                completed_roles=state.completed_roles,
                branch_count=state.branch_count,
                error=str(e),
            )

    def _evaluate_branch(self, role: str, summary: str) -> tuple[bool, Optional[str]]:
        """
        분기 평가 (요약 기반)

        Args:
            role: 현재 역할
            summary: 역할 출력 요약

        Returns:
            (분기 필요 여부, 분기 대상 역할)
        """
        condition = BRANCH_CONDITIONS.get(role)
        if not condition:
            return False, None

        keywords = condition.get("keywords", [])
        summary_lower = summary.lower()

        for keyword in keywords:
            if keyword.lower() in summary_lower:
                return True, condition.get("target")

        return False, None

    def _generate_coaching(self, role: str, summary: str) -> Optional[str]:
        """
        코칭 피드백 생성

        지휘관이 각 역할에게 줄 수 있는 피드백.
        """
        coaching_hints = {
            "ideator": "아이디어가 충분한지 확인. 다양성 부족 시 추가 생성 권장.",
            "analyst": "선별 기준이 명확한지 확인. 편향 여부 점검.",
            "critic": "모든 RULES 위반 여부 확인했는지 점검.",
            "architect": "최소 변경 원칙 준수 여부 확인.",
            "executor": "설계대로만 구현했는지 확인.",
            "validator": "모든 검증 항목 통과 여부 확인.",
        }

        return coaching_hints.get(role)

    def _get_next_hint(self, role: str) -> str:
        """다음 역할을 위한 힌트"""
        hints = {
            "ideator": "아이디어 중 우선순위 평가 필요",
            "analyst": "선별된 항목에 대한 위험 분석 필요",
            "critic": "위험 요소 반영한 설계 필요",
            "architect": "설계대로 구현 필요",
            "executor": "구현 결과 검증 필요",
            "validator": "최종 검증 완료",
        }
        return hints.get(role, "")

    def _build_final_summary(self, state: CommanderState) -> str:
        """최종 요약 생성"""
        parts = [
            f"세션: {state.session_id}",
            f"체인: {state.chain_type.value}",
            f"완료 역할: {', '.join(state.completed_roles)}",
            f"분기 횟수: {state.branch_count}",
            "",
            "역할별 요약:",
        ]

        for role, summary in state.summaries.items():
            parts.append(f"  [{role}] {summary}")

        return "\n".join(parts)

    def get_context_size(self, state: CommanderState) -> int:
        """현재 컨텍스트 크기 추정 (토큰)"""
        total = 0

        # 원본 요청
        total += self.compactor.estimate_tokens(state.user_request)

        # 요약들
        for summary in state.summaries.values():
            total += self.compactor.estimate_tokens(summary)

        # 메타데이터 오버헤드
        total += 500

        return total


# 편의 함수
async def execute_sage_chain(
    session_id: str,
    user_request: str,
    chain_type: ChainType = ChainType.FULL,
) -> ChainResult:
    """Sage 체인 실행 (편의 함수)"""
    commander = SageCommander()
    return await commander.execute_chain(session_id, user_request, chain_type)
