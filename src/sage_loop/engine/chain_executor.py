"""
Chain Executor - 체인 실행 엔진

체인 타입:
    - FULL: Ideator → Analyst → Critic → Architect → Executor → Validator
    - QUICK: Critic → Architect → Executor
    - REVIEW: Critic → Validator
    - DESIGN: Ideator → Analyst → Critic → Architect

체인 선택:
    - 키워드 매칭 기반 자동 선택
    - 복잡도/위험도 평가

실행 모드:
    - v1 (execute_chain): 순차 실행 (기존 방식, 컨텍스트 누적)
    - v2 (execute_chain_v2): SageCommander 기반 (컨텍스트 격리, 권장)
"""

import logging
from typing import Optional

import yaml

from ..config import get_settings
from ..schemas import (
    BranchRule,
    ChainDefinition,
    ChainType,
    ExecutionMode,
    RoleStatus,
    SessionStatus,
    TaskAnalysis,
)
from ..services.state_service import StateService
from .branch_handler import BranchHandler, load_branch_rules_from_config
from .role_runner import RoleRunner

# v2 Components (lazy import to avoid circular)
# from .sage_commander import SageCommander

logger = logging.getLogger(__name__)


# 기본 체인 정의 (CLAUDE.md SAGE_LOOP v3.2 TRIPLE SAGE 기준)
# NOTE: config.yaml이 있으면 거기서 로드됨. 이 값은 폴백용.
DEFAULT_CHAINS = {
    ChainType.FULL: {
        "roles": [
            # Phase 1: Sage 접수 (안건 접수)
            "sage",
            # Phase 2-7: 발산 & 수렴
            "ideator",
            "analyst",
            "critic",
            "censor",
            "academy",
            "architect",
            # Phase 8-9: 의정부 심의 (병렬)
            "left-state-councilor",
            "right-state-councilor",
            # Phase 10: Sage 허가 (실행 허가)
            "sage",
            # Phase 11-13: 실행 & 검증
            "executor",
            "inspector",
            "validator",
            # Phase 14: Sage 결재 (최종 결재)
            "sage",
            # Phase 15-17: 사후 처리
            "historian",
            "reflector",
            "improver",
        ],
        "triggers": {
            "keywords": ["새로운", "개발", "구현", "기능", "추가", "만들어"],
            "complexity": ["중간", "복잡"],
            "risk": ["보통", "높음"],
        },
    },
    ChainType.QUICK: {
        "roles": [
            "sage",  # 접수
            "critic",
            "architect",
            "executor",
            "validator",
            "sage",  # 결재
            "historian",
        ],
        "triggers": {
            "keywords": ["버그", "수정", "고침", "패치", "에러", "오류"],
            "complexity": ["단순", "중간"],
            "risk": ["낮음", "보통"],
        },
    },
    ChainType.REVIEW: {
        "roles": ["critic", "validator"],
        "triggers": {
            "keywords": ["검토", "리뷰", "확인", "체크", "점검"],
            "complexity": ["단순"],
            "risk": ["낮음"],
        },
    },
    ChainType.DESIGN: {
        "roles": [
            "sage",  # 접수
            "ideator",
            "analyst",
            "critic",
            "architect",
        ],
        "triggers": {
            "keywords": ["설계", "아키텍처", "구조", "계획", "방향"],
            "complexity": ["중간", "복잡"],
            "risk": ["보통"],
        },
    },
}

# 모드 선택 키워드
MODE_KEYWORDS = {
    ExecutionMode.FULL_AUTO: ["긴급", "빨리", "수정", "버그", "패치", "hotfix"],
    ExecutionMode.PLAN_FIRST: [
        "신규",
        "기능",
        "개발",
        "구현",
        "추가",
        "new",
        "feature",
    ],
    ExecutionMode.INTERACTIVE: ["복잡", "불확실", "리스크", "위험", "마이그레이션"],
}


class ChainExecutor:
    """체인 실행 엔진"""

    def __init__(self, state_service: StateService):
        self.state_service = state_service
        self.role_runner = RoleRunner(state_service)
        self.branch_handler = BranchHandler(state_service)

        # 설정 로드
        self._config: Optional[dict] = None
        self._chains = DEFAULT_CHAINS
        self._load_config()

    def _load_config(self) -> None:
        """config.yaml 로드"""
        try:
            settings = get_settings()
            config_path = settings.get_config_path()

            with open(config_path) as f:
                self._config = yaml.safe_load(f)

            # 체인 정의 로드
            if "chains" in self._config:
                for chain_name, chain_def in self._config["chains"].items():
                    try:
                        chain_type = ChainType(chain_name)
                        self._chains[chain_type] = chain_def
                    except ValueError:
                        logger.warning(f"Unknown chain type: {chain_name}")

            # 분기 규칙 로드
            branch_rules = load_branch_rules_from_config(self._config)
            if branch_rules:
                self.branch_handler = BranchHandler(self.state_service, branch_rules)

            logger.info(f"Loaded config from {config_path}")

        except FileNotFoundError:
            logger.warning("Config file not found, using defaults")
        except Exception as e:
            logger.error(f"Config load error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # Task Analysis
    # ═══════════════════════════════════════════════════════════════

    async def analyze_task(self, user_request: str) -> TaskAnalysis:
        """
        작업 분석

        Args:
            user_request: 사용자 요청 텍스트

        Returns:
            TaskAnalysis: 분석 결과 (타입, 복잡도, 위험도)
        """
        text = user_request.lower()

        # 작업 유형 판단
        if any(kw in text for kw in ["버그", "수정", "고침", "에러", "오류"]):
            task_type = "수정"
        elif any(kw in text for kw in ["검토", "리뷰", "확인"]):
            task_type = "검토"
        elif any(kw in text for kw in ["설계", "아키텍처", "구조"]):
            task_type = "설계"
        else:
            task_type = "신규"

        # 복잡도 판단
        if any(kw in text for kw in ["간단", "쉬운", "빠른", "단순"]):
            complexity = "단순"
        elif any(kw in text for kw in ["복잡", "어려운", "대규모", "마이그레이션"]):
            complexity = "복잡"
        else:
            complexity = "중간"

        # 위험도 판단
        if any(kw in text for kw in ["위험", "주의", "조심", "프로덕션", "데이터"]):
            risk = "높음"
        elif any(kw in text for kw in ["안전", "테스트", "로컬"]):
            risk = "낮음"
        else:
            risk = "보통"

        # 매칭된 키워드 수집
        matched_keywords = []
        for chain_def in self._chains.values():
            triggers = chain_def.get("triggers", {})
            keywords = triggers.get("keywords", [])
            matched_keywords.extend([kw for kw in keywords if kw in text])

        return TaskAnalysis(
            task_type=task_type,
            complexity=complexity,
            risk=risk,
            matched_keywords=list(set(matched_keywords)),
        )

    async def select_chain(self, analysis: TaskAnalysis) -> ChainType:
        """
        체인 선택

        Args:
            analysis: 작업 분석 결과

        Returns:
            ChainType: 선택된 체인 타입
        """
        # 키워드 매칭 점수 계산
        scores = {}

        for chain_type, chain_def in self._chains.items():
            triggers = chain_def.get("triggers", {})
            score = 0

            # 키워드 매칭
            keywords = triggers.get("keywords", [])
            for kw in analysis.matched_keywords:
                if kw in keywords:
                    score += 1

            # 복잡도 매칭
            if analysis.complexity in triggers.get("complexity", []):
                score += 2

            # 위험도 매칭
            if analysis.risk in triggers.get("risk", []):
                score += 1

            scores[chain_type] = score

        # 최고 점수 체인 선택
        if scores:
            best_chain = max(scores, key=scores.get)
            if scores[best_chain] > 0:
                return best_chain

        # 기본값: FULL
        return ChainType.FULL

    async def select_mode(self, user_request: str, analysis: TaskAnalysis) -> ExecutionMode:
        """
        실행 모드 선택

        Args:
            user_request: 사용자 요청 텍스트
            analysis: 작업 분석 결과

        Returns:
            ExecutionMode: 선택된 실행 모드
        """
        text = user_request.lower()

        # 키워드 매칭
        for mode, keywords in MODE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return mode

        # 복잡도/위험도 기반 선택
        if analysis.complexity == "복잡" or analysis.risk == "높음":
            return ExecutionMode.INTERACTIVE
        elif analysis.task_type == "수정" and analysis.complexity == "단순":
            return ExecutionMode.FULL_AUTO

        # 기본값
        return ExecutionMode.PLAN_FIRST

    # ═══════════════════════════════════════════════════════════════
    # Chain Execution
    # ═══════════════════════════════════════════════════════════════

    async def execute_chain(self, session_id: str) -> None:
        """
        체인 실행 (백그라운드)

        Args:
            session_id: 세션 ID
        """
        logger.info(f"[{session_id}] Starting chain execution")

        try:
            # 세션 조회
            session = await self.state_service.get_session(session_id)
            if not session:
                logger.error(f"[{session_id}] Session not found")
                return

            # 체인 정의 조회
            chain_def = self._chains.get(session.chain_type)
            if not chain_def:
                logger.error(f"[{session_id}] Chain not found: {session.chain_type}")
                await self.state_service.update_status(session_id, SessionStatus.FAILED, error="Chain not found")
                return

            roles = chain_def.get("roles", [])

            # 체인 상태 초기화
            await self.state_service.init_chain_state(session_id, session.chain_type, roles)

            # 이미 완료된 역할 이후부터 시작
            start_idx = len(session.completed_roles)

            # 역할 순차 실행
            for i, role in enumerate(roles[start_idx:], start=start_idx):
                # 현재 역할 업데이트
                await self.state_service.update_current_role(session_id, role)

                # 역할 실행
                result = await self.role_runner.execute(session_id, role)

                if result.status == RoleStatus.FAILED:
                    logger.error(f"[{session_id}] Role {role} failed: {result.error}")
                    await self.state_service.update_status(session_id, SessionStatus.FAILED, error=result.error)
                    return

                # 분기 평가
                branch_decision = await self.branch_handler.evaluate(session_id, role, result)

                if branch_decision.action == "branch":
                    # 분기 역할 실행
                    logger.info(f"[{session_id}] Branching to {branch_decision.target_role}")
                    branch_result = await self.role_runner.execute(session_id, branch_decision.target_role)

                    if branch_result.status == RoleStatus.FAILED:
                        logger.warning(f"[{session_id}] Branch role failed, continuing main chain")

                elif branch_decision.action == "escalate":
                    # 사용자 개입 요청
                    logger.warning(f"[{session_id}] Escalating: {branch_decision.reason}")
                    await self.state_service.update_status(session_id, SessionStatus.WAITING_APPROVAL)
                    return

                # interactive 모드: 각 역할 후 승인 대기
                session_state = await self.state_service.get_session(session_id)
                if session_state and session_state.mode == ExecutionMode.INTERACTIVE:
                    if i < len(roles) - 1:  # 마지막 역할이 아니면
                        await self.state_service.update_status(session_id, SessionStatus.WAITING_APPROVAL)
                        return

            # 체인 완료
            await self.state_service.update_status(session_id, SessionStatus.COMPLETED)
            logger.info(f"[{session_id}] Chain completed successfully")

        except Exception as e:
            logger.error(f"[{session_id}] Chain execution error: {e}")
            await self.state_service.update_status(session_id, SessionStatus.FAILED, error=str(e))

    # ═══════════════════════════════════════════════════════════════
    # Chain Definitions
    # ═══════════════════════════════════════════════════════════════

    def get_chain_definitions(self) -> list[ChainDefinition]:
        """모든 체인 정의 반환"""
        definitions = []

        for chain_type, chain_def in self._chains.items():
            branches = []
            if self._config and "chains" in self._config:
                config_chain = self._config["chains"].get(chain_type.value, {})
                for b in config_chain.get("branches", []):
                    branches.append(
                        BranchRule(
                            from_role=b["from"],
                            to_role=b["to"],
                            condition=b["condition"],
                            max_loops=b.get("max_loops", 3),
                        )
                    )

            definitions.append(
                ChainDefinition(
                    name=chain_type.value,
                    roles=chain_def.get("roles", []),
                    triggers=chain_def.get("triggers", {}),
                    branches=branches,
                )
            )

        return definitions

    def get_chain_definition(self, chain_type: ChainType) -> Optional[ChainDefinition]:
        """특정 체인 정의 반환"""
        chain_def = self._chains.get(chain_type)
        if not chain_def:
            return None

        branches = []
        if self._config and "chains" in self._config:
            config_chain = self._config["chains"].get(chain_type.value, {})
            for b in config_chain.get("branches", []):
                branches.append(
                    BranchRule(
                        from_role=b["from"],
                        to_role=b["to"],
                        condition=b["condition"],
                        max_loops=b.get("max_loops", 3),
                    )
                )

        return ChainDefinition(
            name=chain_type.value,
            roles=chain_def.get("roles", []),
            triggers=chain_def.get("triggers", {}),
            branches=branches,
        )

    # ═══════════════════════════════════════════════════════════════
    # Chain Execution v2 (컨텍스트 격리)
    # ═══════════════════════════════════════════════════════════════

    async def execute_chain_v2(
        self,
        session_id: str,
        user_request: str,
        chain_type: Optional[ChainType] = None,
    ) -> dict:
        """
        체인 실행 v2 (SageCommander 기반)

        컨텍스트 격리를 통해 효율적인 실행.
        각 역할은 독립된 Task로 실행됨.

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청
            chain_type: 체인 타입 (None이면 자동 선택)

        Returns:
            dict: 실행 결과 {status, final_summary, completed_roles, ...}
        """
        # Lazy import to avoid circular dependency
        from .sage_commander import SageCommander

        logger.info(f"[{session_id}] Starting chain execution v2 (SageCommander)")

        # 체인 타입 결정
        if chain_type is None:
            analysis = await self.analyze_task(user_request)
            chain_type = await self.select_chain(analysis)

        # SageCommander로 실행
        commander = SageCommander(self.state_service)
        result = await commander.execute_chain(
            session_id=session_id,
            user_request=user_request,
            chain_type=chain_type,
        )

        # 결과를 dict로 변환
        return {
            "session_id": result.session_id,
            "status": result.status,
            "final_summary": result.final_summary,
            "completed_roles": result.completed_roles,
            "branch_count": result.branch_count,
            "error": result.error,
        }
