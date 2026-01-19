"""
Task Dispatcher - Task 기반 역할 디스패처

Task 도구를 활용하여 역할별 서브에이전트를 생성.
각 역할은 독립된 컨텍스트에서 실행됨.

동작 방식:
    1. 역할 실행 지시 생성 (Task 프롬프트)
    2. 전체 출력을 Redis에 저장
    3. 압축된 요약만 Sage로 반환

참고:
    Task 도구는 Claude Code의 도구이므로,
    이 클래스는 Task 호출을 위한 인터페이스와 결과 처리를 담당.
    실제 Task 호출은 Claude Code 세션에서 이루어짐.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from ..services.state_service import StateService
from .context_compactor import CompactedOutput, ContextCompactor

logger = logging.getLogger(__name__)


@dataclass
class TaskRequest:
    """Task 도구 호출 요청"""

    description: str  # 3-5 단어 요약
    prompt: str  # 상세 지시
    subagent_type: str  # 에이전트 타입 (general-purpose, Explore, Plan 등)
    run_in_background: bool = False
    model: Optional[str] = None  # sonnet, opus, haiku


@dataclass
class TaskResult:
    """Task 실행 결과"""

    role: str
    status: str  # completed, failed, timeout
    output: dict[str, Any]  # 전체 출력
    summary: str  # 압축된 요약
    redis_key: str  # Redis 저장 키
    started_at: str
    completed_at: str
    error: Optional[str] = None


# 역할별 Task 설정
ROLE_TASK_CONFIG = {
    "ideator": {
        "description": "아이디어 브레인스토밍",
        "subagent_type": "general-purpose",
        "model": "haiku",  # 빠른 아이디어 생성
        "prompt_template": """
역할: Ideator (아이디어 생성자)
임무: 주어진 요청에 대해 다양한 아이디어를 생성하라.

요청: {user_request}

출력 형식 (JSON):
{{
    "ideas": [
        {{"title": "제목", "description": "설명", "category": "분류"}}
    ],
    "count": 아이디어_수,
    "categories": ["분류1", "분류2"]
}}

제약: 판단 없이 발산적으로 생성. 최소 10개 이상.
""",
    },
    "analyst": {
        "description": "아이디어 분석 및 선별",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """
역할: Analyst (분석가)
임무: 아이디어를 분석하고 실현 가능한 것을 선별하라.

입력:
{previous_summary}

출력 형식 (JSON):
{{
    "selected": [{{"idea": "제목", "reason": "선정 이유", "priority": 1-5}}],
    "excluded": [{{"idea": "제목", "reason": "제외 이유"}}],
    "criteria": "선별 기준 요약",
    "key_items": ["핵심 항목1", "핵심 항목2"]
}}

제약: 객관적 기준으로 선별. 새 아이디어 추가 금지.
""",
    },
    "critic": {
        "description": "위험 및 제약 분석",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """
역할: Critic (비평가)
임무: 선별된 항목의 위험과 제약을 분석하라.

입력:
{previous_summary}

출력 형식 (JSON):
{{
    "risk_level": "높음|보통|낮음",
    "issues": [{{"type": "유형", "description": "설명", "severity": 1-5}}],
    "issue_count": 이슈_수,
    "top_issues": ["주요 이슈1", "주요 이슈2"],
    "recommendations": ["권장 조치1", "권장 조치2"]
}}

제약: RULES 위반 여부 반드시 확인 (라이선스, 보안 등).
""",
    },
    "architect": {
        "description": "설계 및 구조 결정",
        "subagent_type": "Plan",  # Plan 에이전트 활용
        "model": "sonnet",
        "prompt_template": """
역할: Architect (설계자)
임무: 위험을 반영하여 구현 설계를 작성하라.

입력:
{previous_summary}

출력 형식 (JSON):
{{
    "design_type": "설계 유형",
    "components": ["컴포넌트1", "컴포넌트2"],
    "dependencies": ["의존성1", "의존성2"],
    "files_to_modify": ["파일 경로1", "파일 경로2"],
    "implementation_steps": ["단계1", "단계2", "단계3"]
}}

제약: 최소 변경 원칙. 기존 패턴 준수.
""",
    },
    "executor": {
        "description": "설계 구현 실행",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """
역할: Executor (실행자)
임무: 설계대로 구현하라. 판단/설계/비판 없이 오직 실행만.

입력:
{previous_summary}

출력 형식 (JSON):
{{
    "status": "completed|failed",
    "changes": ["변경사항1", "변경사항2"],
    "files": ["수정된 파일1", "수정된 파일2"],
    "commands_run": ["실행된 명령1"]
}}

제약: 설계대로만 구현. 추가 판단 금지.
""",
    },
    "validator": {
        "description": "구현 결과 검증",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: Validator | 임무: 검증
입력: {previous_summary}
출력: {{"result": "passed|failed", "passed": N, "total": N, "issues": []}}""",
    },
    "censor": {
        "description": "RULES 위반 사전 봉쇄",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: Censor | 임무: RULES 위반 사전 검사
입력: {previous_summary}
출력: {{"status": "clean|violation", "violations": [], "blocked_items": []}}""",
    },
    "academy": {
        "description": "학술 자문 및 근거 제공",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: Academy | 임무: 근거/선례 제공
입력: {previous_summary}
출력: {{"evidence_count": N, "references": [], "recommendations": []}}""",
    },
    "left-state-councilor": {
        "description": "내정 검토 (인사/재정/의례)",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: LeftState (좌의정) | 임무: 내정 검토
입력: {previous_summary}
출력: {{"approval": "승인|보류|거부", "opinion": "의견", "conditions": []}}""",
    },
    "right-state-councilor": {
        "description": "실무 검토 (병조/형조/공조)",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: RightState (우의정) | 임무: 실무 검토
입력: {previous_summary}
출력: {{"approval": "승인|보류|거부", "opinion": "의견", "conditions": []}}""",
    },
    "inspector": {
        "description": "실행 결과 감찰",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: Inspector | 임무: 실행 결과 감찰
입력: {previous_summary}
출력: {{"result": "pass|fail", "issues": [], "severity": "low|medium|high"}}""",
    },
    "historian": {
        "description": "이력 기록",
        "subagent_type": "general-purpose",
        "model": "haiku",
        "prompt_template": """역할: Historian | 임무: 세션 이력 기록
입력: {previous_summary}
출력: {{"status": "recorded", "session_key": "키", "summary": "요약"}}""",
    },
    "reflector": {
        "description": "회고 및 교훈 도출",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: Reflector | 임무: 회고 및 교훈
입력: {previous_summary}
출력: {{"lessons_count": N, "key_lessons": [], "improvements": []}}""",
    },
    "improver": {
        "description": "개선 사항 도출",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: Improver | 임무: 개선 사항 도출
입력: {previous_summary}
출력: {{"improvements_count": N, "priority_items": [], "next_actions": []}}""",
    },
    "feasibility-checker": {
        "description": "실현 가능성 검토 (분기 역할)",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: FeasibilityChecker | 임무: 기술/자원/시간 제약 검토
입력: {previous_summary}
출력: {{"feasibility": "가능|불가능|조건부", "constraints": []}}""",
    },
    "constraint-enforcer": {
        "description": "제약 조건 강제 (분기 역할)",
        "subagent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": """역할: ConstraintEnforcer | 임무: RULES 위반 확인 및 대안 제시
입력: {previous_summary}
출력: {{"status": "clean|violation", "resolutions": []}}""",
    },
}


class TaskDispatcher:
    """Task 기반 역할 디스패처 - 컨텍스트 격리"""

    def __init__(self, state_service: StateService):
        self.state_service = state_service
        self.compactor = ContextCompactor()
        self.configs = ROLE_TASK_CONFIG

    def build_task_request(
        self,
        role: str,
        user_request: str,
        previous_summary: str = "",
    ) -> TaskRequest:
        """
        Task 도구 호출 요청 생성

        Args:
            role: 역할 이름
            user_request: 원본 사용자 요청
            previous_summary: 이전 역할들의 압축된 요약

        Returns:
            TaskRequest: Task 도구 호출에 필요한 정보
        """
        config = self.configs.get(role, {})

        prompt = config.get("prompt_template", "역할: {role}\n요청: {user_request}").format(
            user_request=user_request,
            previous_summary=previous_summary or "없음",
            role=role,
        )

        return TaskRequest(
            description=config.get("description", f"{role} 역할 실행"),
            prompt=prompt,
            subagent_type=config.get("subagent_type", "general-purpose"),
            model=config.get("model"),
            run_in_background=False,
        )

    async def dispatch(
        self,
        session_id: str,
        role: str,
        user_request: str,
        previous_outputs: dict[str, CompactedOutput],
    ) -> TaskResult:
        """
        역할 실행 디스패치

        실제 Task 호출은 Claude Code 세션에서 이루어지며,
        이 메서드는 결과 처리를 담당.

        Args:
            session_id: 세션 ID
            role: 역할 이름
            user_request: 원본 사용자 요청
            previous_outputs: 이전 역할들의 압축된 출력

        Returns:
            TaskResult: 실행 결과
        """
        started_at = datetime.now().isoformat()

        # 이전 역할 요약 준비
        previous_summary = self.compactor.prepare_input(role, previous_outputs)

        # Task 요청 생성
        task_request = self.build_task_request(role, user_request, previous_summary)

        # Redis 키 준비
        redis_key = f"sage:role:{session_id}:{role}"

        try:
            # Task 실행 (실제로는 Claude Code에서 호출됨)
            # 여기서는 시뮬레이션 또는 Hook을 통한 결과 수신
            output = await self._execute_task(session_id, role, task_request)

            # 전체 출력을 Redis에 저장
            await self._save_to_redis(session_id, role, output)

            # 출력 압축
            compacted = self.compactor.compact(role, output)

            completed_at = datetime.now().isoformat()

            return TaskResult(
                role=role,
                status="completed",
                output=output,
                summary=compacted.summary,
                redis_key=redis_key,
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            logger.error(f"[{session_id}] Task dispatch error for {role}: {e}")
            completed_at = datetime.now().isoformat()

            return TaskResult(
                role=role,
                status="failed",
                output={},
                summary=f"실패: {str(e)}",
                redis_key=redis_key,
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
            )

    async def _execute_task(
        self,
        session_id: str,
        role: str,
        request: TaskRequest,
    ) -> dict[str, Any]:
        """
        Task 실행 (인터페이스)

        실제 구현은 두 가지 방식:
        1. Hook을 통한 Claude Code Task 도구 호출
        2. 기존 RoleRunner를 통한 직접 실행 (폴백)

        현재는 RoleRunner 폴백 사용.
        """
        from .role_runner import RoleRunner

        # 폴백: 기존 RoleRunner 사용
        role_runner = RoleRunner(self.state_service)
        result = await role_runner.execute(session_id, role)

        # RoleOutput을 dict로 변환
        return {
            "status": result.status.value,
            "output": result.output,
            "error": result.error,
        }

    async def _save_to_redis(
        self,
        session_id: str,
        role: str,
        output: dict[str, Any],
    ) -> None:
        """Redis에 전체 출력 저장"""
        try:
            redis_key = f"sage:role:{session_id}:{role}"
            await self.state_service.save_role_output(session_id, role, output)
            logger.debug(f"[{session_id}] Saved {role} output to {redis_key}")
        except Exception as e:
            logger.warning(f"[{session_id}] Redis save failed for {role}: {e}")

    def get_task_json(self, request: TaskRequest) -> str:
        """
        Task 도구 호출용 JSON 생성

        Claude Code에서 직접 사용할 수 있는 형식.
        """
        return json.dumps(
            {
                "description": request.description,
                "prompt": request.prompt,
                "subagent_type": request.subagent_type,
                "run_in_background": request.run_in_background,
                "model": request.model,
            },
            ensure_ascii=False,
            indent=2,
        )


# 편의 함수
def build_role_task(
    role: str,
    user_request: str,
    previous_summary: str = "",
) -> TaskRequest:
    """역할 Task 요청 생성 (편의 함수)"""
    from ..services.state_service import StateService

    dispatcher = TaskDispatcher(StateService())
    return dispatcher.build_task_request(role, user_request, previous_summary)
