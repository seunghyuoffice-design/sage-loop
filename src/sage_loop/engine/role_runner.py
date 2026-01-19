"""
Role Runner - 개별 역할 실행기

역할 실행 흐름:
    1. 역할 컨텍스트 준비 (이전 역할 출력 참조)
    2. 역할별 시스템 프롬프트 로드
    3. 역할 실행 (실제 처리 또는 스텁)
    4. 출력 검증
    5. 코칭 피드백 생성
"""

import logging
from datetime import datetime
from typing import Any, Optional

from ..schemas import RoleOutput, RoleStatus
from ..services.state_service import StateService

logger = logging.getLogger(__name__)


def validate_json_schema(data: dict, schema: dict) -> tuple[bool, list[str]]:
    """간단한 JSON 스키마 검증 (jsonschema 의존성 없이)"""
    errors = []

    # 필수 키 검증
    required = schema.get("required", [])
    for key in required:
        if key not in data:
            errors.append(f"필수 키 누락: {key}")

    # 속성별 검증
    properties = schema.get("properties", {})
    for key, prop_schema in properties.items():
        if key not in data:
            continue

        value = data[key]
        prop_type = prop_schema.get("type")

        # 타입 검증
        if prop_type == "array" and not isinstance(value, list):
            errors.append(f"{key}: 배열 타입 필요")
        elif prop_type == "string" and not isinstance(value, str):
            errors.append(f"{key}: 문자열 타입 필요")
        elif prop_type == "integer" and not isinstance(value, int):
            errors.append(f"{key}: 정수 타입 필요")
        elif prop_type == "object" and not isinstance(value, dict):
            errors.append(f"{key}: 객체 타입 필요")

        # 배열 길이 검증
        if prop_type == "array" and isinstance(value, list):
            min_items = prop_schema.get("minItems")
            max_items = prop_schema.get("maxItems")
            if min_items and len(value) < min_items:
                errors.append(f"{key}: 최소 {min_items}개 필요, {len(value)}개 제공됨")
            if max_items and len(value) > max_items:
                errors.append(f"{key}: 최대 {max_items}개 허용, {len(value)}개 제공됨")

        # enum 검증
        enum_values = prop_schema.get("enum")
        if enum_values and value not in enum_values:
            errors.append(f"{key}: 허용값 {enum_values} 중 하나여야 함, '{value}' 제공됨")

        # 정수 최소값 검증
        if prop_type == "integer" and isinstance(value, int):
            minimum = prop_schema.get("minimum")
            if minimum and value < minimum:
                errors.append(f"{key}: 최소값 {minimum} 필요, {value} 제공됨")

    return len(errors) == 0, errors


# 역할별 JSON 스키마 (출력 형식 강제)
ROLE_JSON_SCHEMAS = {
    "ideator": {
        "type": "object",
        "required": ["ideas", "count"],
        "properties": {
            "ideas": {"type": "array", "minItems": 50, "items": {"type": "string"}},
            "count": {"type": "integer", "minimum": 50},
        },
    },
    "analyst": {
        "type": "object",
        "required": ["selected", "key_items"],
        "properties": {
            "selected": {"type": "array", "minItems": 8, "maxItems": 12},
            "key_items": {"type": "array"},
        },
    },
    "critic": {
        "type": "object",
        "required": ["risk_level", "top_issues"],
        "properties": {
            "risk_level": {"type": "string", "enum": ["낮음", "보통", "높음"]},
            "top_issues": {"type": "array"},
        },
    },
    "censor": {
        "type": "object",
        "required": ["status", "violations"],
        "properties": {
            "status": {"type": "string", "enum": ["clean", "violation"]},
            "violations": {"type": "array"},
        },
    },
    "academy": {
        "type": "object",
        "required": ["evidence_count", "references"],
        "properties": {
            "evidence_count": {"type": "integer"},
            "references": {"type": "array"},
        },
    },
    "architect": {
        "type": "object",
        "required": ["design_type", "components"],
        "properties": {
            "design_type": {"type": "string"},
            "components": {"type": "array", "minItems": 3, "maxItems": 5},
        },
    },
    "left-state-councilor": {
        "type": "object",
        "required": ["approval", "opinion"],
        "properties": {
            "approval": {"type": "string", "enum": ["승인", "보류", "거부"]},
            "opinion": {"type": "string"},
        },
    },
    "right-state-councilor": {
        "type": "object",
        "required": ["approval", "opinion"],
        "properties": {
            "approval": {"type": "string", "enum": ["승인", "보류", "거부"]},
            "opinion": {"type": "string"},
        },
    },
    "executor": {
        "type": "object",
        "required": ["status", "files"],
        "properties": {
            "status": {"type": "string", "enum": ["completed", "failed"]},
            "files": {"type": "array"},
        },
    },
    "inspector": {
        "type": "object",
        "required": ["result", "issues"],
        "properties": {
            "result": {"type": "string", "enum": ["pass", "fail"]},
            "issues": {"type": "array"},
        },
    },
    "validator": {
        "type": "object",
        "required": ["result", "passed", "total"],
        "properties": {
            "result": {"type": "string", "enum": ["passed", "failed"]},
            "passed": {"type": "integer"},
            "total": {"type": "integer"},
        },
    },
    "historian": {
        "type": "object",
        "required": ["status", "session_key"],
        "properties": {
            "status": {"type": "string"},
            "session_key": {"type": "string"},
        },
    },
    "reflector": {
        "type": "object",
        "required": ["lessons_count", "key_lessons"],
        "properties": {
            "lessons_count": {"type": "integer"},
            "key_lessons": {"type": "array"},
        },
    },
    "improver": {
        "type": "object",
        "required": ["improvements_count", "priority_items"],
        "properties": {
            "improvements_count": {"type": "integer"},
            "priority_items": {"type": "array"},
        },
    },
    "feasibility-checker": {
        "type": "object",
        "required": ["feasibility", "constraints"],
        "properties": {
            "feasibility": {"type": "string", "enum": ["가능", "불가능", "조건부"]},
            "constraints": {"type": "array"},
        },
    },
    "constraint-enforcer": {
        "type": "object",
        "required": ["status", "resolutions"],
        "properties": {
            "status": {"type": "string", "enum": ["clean", "violation"]},
            "resolutions": {"type": "array"},
        },
    },
}

# 역할별 시스템 프롬프트 (JSON 출력 강제)
ROLE_PROMPTS = {
    "ideator": """아이디어 대량 생성. 최소 50개. 발산적 사고.
출력 형식 (JSON 필수):
{"ideas": ["아이디어1", ...], "count": 50}""",
    "analyst": """8-12개 선별. 중복 제거, 핵심 추출.
출력 형식 (JSON 필수):
{"selected": ["항목1", ...], "key_items": ["핵심1", ...]}""",
    "critic": """논리적 결함, 숨은 비용, 실패 시나리오 분석.
출력 형식 (JSON 필수):
{"risk_level": "낮음|보통|높음", "top_issues": ["이슈1", ...]}""",
    "censor": """RULES 위반 사전 검사. 위반 항목 봉쇄.
출력 형식 (JSON 필수):
{"status": "clean|violation", "violations": []}""",
    "academy": """학술 근거, 선례 제공. 참조 자료 첨부.
출력 형식 (JSON 필수):
{"evidence_count": N, "references": ["참조1", ...]}""",
    "architect": """3-5개 컴포넌트 설계. 모듈화, 확장성.
출력 형식 (JSON 필수):
{"design_type": "설계유형", "components": ["컴포넌트1", ...]}""",
    "left-state-councilor": """내정 검토 (인사/재정/의례). 승인/보류/거부.
출력 형식 (JSON 필수):
{"approval": "승인|보류|거부", "opinion": "의견"}""",
    "right-state-councilor": """실무 검토 (병조/형조/공조). 승인/보류/거부.
출력 형식 (JSON 필수):
{"approval": "승인|보류|거부", "opinion": "의견"}""",
    "executor": """설계대로 구현. 판단 없이 실행만.
출력 형식 (JSON 필수):
{"status": "completed|failed", "files": ["파일1", ...]}""",
    "inspector": """실행 결과 감찰. 이슈 식별.
출력 형식 (JSON 필수):
{"result": "pass|fail", "issues": []}""",
    "validator": """스키마/수량 검증. 최종 통과 여부.
출력 형식 (JSON 필수):
{"result": "passed|failed", "passed": N, "total": N}""",
    "historian": """세션 이력 기록. 요약 저장.
출력 형식 (JSON 필수):
{"status": "recorded", "session_key": "키"}""",
    "reflector": """회고 및 교훈 도출.
출력 형식 (JSON 필수):
{"lessons_count": N, "key_lessons": ["교훈1", ...]}""",
    "improver": """개선 사항 도출. 다음 액션 제시.
출력 형식 (JSON 필수):
{"improvements_count": N, "priority_items": ["개선1", ...]}""",
    "feasibility-checker": """기술/자원/시간 제약 검토.
출력 형식 (JSON 필수):
{"feasibility": "가능|불가능|조건부", "constraints": []}""",
    "constraint-enforcer": """RULES 위반 확인, 대안 제시.
출력 형식 (JSON 필수):
{"status": "clean|violation", "resolutions": []}""",
}

# 역할별 예상 출력 키 (15단계)
ROLE_OUTPUT_KEYS = {
    "ideator": ["ideas", "count"],
    "analyst": ["selected", "key_items"],
    "critic": ["risk_level", "top_issues"],
    "censor": ["status", "violations"],
    "academy": ["evidence_count", "references"],
    "architect": ["design_type", "components"],
    "left-state-councilor": ["approval", "opinion"],
    "right-state-councilor": ["approval", "opinion"],
    "executor": ["status", "files"],
    "inspector": ["result", "issues"],
    "validator": ["result", "passed", "total"],
    "historian": ["status", "session_key"],
    "reflector": ["lessons_count", "key_lessons"],
    "improver": ["improvements_count", "priority_items"],
    "feasibility-checker": ["feasibility", "constraints"],
    "constraint-enforcer": ["status", "resolutions"],
}


class RoleRunner:
    """역할 실행기"""

    def __init__(self, state_service: StateService):
        self.state_service = state_service

    async def execute(
        self,
        session_id: str,
        role: str,
        context: Optional[dict[str, Any]] = None,
    ) -> RoleOutput:
        """
        역할 실행

        Args:
            session_id: 세션 ID
            role: 역할 이름
            context: 추가 컨텍스트 (이전 역할 출력 등)

        Returns:
            RoleOutput: 역할 실행 결과
        """
        logger.info(f"[{session_id}] Starting role: {role}")
        started_at = datetime.utcnow()

        try:
            # 1. 컨텍스트 준비
            full_context = await self._prepare_context(session_id, role, context)

            # 2. 역할 실행
            output = await self._run_role(role, full_context)

            # 3. 출력 검증
            is_valid, validation_errors = self._validate_output(role, output)

            if not is_valid:
                logger.warning(f"[{session_id}] {role} output validation failed: {validation_errors}")

            # 4. 코칭 피드백 생성
            coaching = self._generate_coaching(role, output, is_valid)

            # 5. 결과 저장
            await self.state_service.save_role_output(session_id, role, output, coaching)
            await self.state_service.add_completed_role(session_id, role)

            completed_at = datetime.utcnow()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            logger.info(f"[{session_id}] Completed role: {role} ({duration_ms:.0f}ms)")

            return RoleOutput(
                role=role,
                status=RoleStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                output=output,
                coaching=coaching,
            )

        except Exception as e:
            logger.error(f"[{session_id}] Role {role} failed: {e}")

            return RoleOutput(
                role=role,
                status=RoleStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e),
            )

    async def _prepare_context(
        self,
        session_id: str,
        role: str,
        extra_context: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """역할 실행을 위한 컨텍스트 준비"""
        context = {
            "session_id": session_id,
            "role": role,
            "system_prompt": ROLE_PROMPTS.get(role, ""),
        }

        # 이전 역할 출력 추가
        previous_outputs = await self.state_service.get_all_role_outputs(session_id)
        if previous_outputs:
            context["previous_roles"] = {r: o.output for r, o in previous_outputs.items() if o.output}

        # 추가 컨텍스트 병합
        if extra_context:
            context.update(extra_context)

        return context

    async def _run_role(self, role: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        역할 실행 (실제 구현 시 Claude API 호출)

        현재는 스텁으로 구현. 실제 구현 시:
        1. Claude Code의 Skill tool 호출
        2. 또는 직접 Claude API 호출
        """
        # 역할별 스텁 출력
        if role == "ideator":
            return {
                "ideas": [f"아이디어 {i+1}" for i in range(50)],
                "count": 50,
            }

        elif role == "analyst":
            return {
                "selected": ["선별 항목 1", "선별 항목 2", "선별 항목 3"],
                "key_items": ["핵심 1", "핵심 2"],
            }

        elif role == "critic":
            return {
                "risk_level": "보통",
                "top_issues": ["잠재적 위험 1", "잠재적 위험 2"],
            }

        elif role == "architect":
            return {
                "design_type": "모듈화 설계",
                "components": ["컴포넌트 A", "컴포넌트 B", "컴포넌트 C"],
            }

        elif role == "executor":
            return {
                "status": "completed",
                "files": ["src/main.py", "tests/test_main.py"],
            }

        elif role == "validator":
            return {
                "result": "passed",
                "passed": 5,
                "total": 5,
            }

        elif role == "feasibility-checker":
            return {
                "feasibility": "가능",
                "constraints": ["시간 제약", "리소스 제약"],
                "alternatives": ["대안 A", "대안 B"],
            }

        elif role == "constraint-enforcer":
            return {"status": "clean", "resolutions": []}

        elif role == "censor":
            return {"status": "clean", "violations": []}

        elif role == "academy":
            return {"evidence_count": 3, "references": ["참조1", "참조2"]}

        elif role == "left-state-councilor":
            return {"approval": "승인", "opinion": "내정 검토 완료"}

        elif role == "right-state-councilor":
            return {"approval": "승인", "opinion": "실무 검토 완료"}

        elif role == "inspector":
            return {"result": "pass", "issues": []}

        elif role == "historian":
            return {"status": "recorded", "session_key": context.get("session_id", "unknown")}

        elif role == "reflector":
            return {"lessons_count": 2, "key_lessons": ["교훈1", "교훈2"]}

        elif role == "improver":
            return {"improvements_count": 2, "priority_items": ["개선1", "개선2"]}

        return {"message": f"{role} 역할 완료"}

    def _validate_output(self, role: str, output: dict[str, Any]) -> tuple[bool, list[str]]:
        """출력 검증 (JSON 스키마 기반)"""
        # JSON 스키마 검증
        schema = ROLE_JSON_SCHEMAS.get(role)
        if schema:
            is_valid, schema_errors = validate_json_schema(output, schema)
            if not is_valid:
                return False, schema_errors

        # 기존 키 검증 (폴백)
        errors = []
        expected_keys = ROLE_OUTPUT_KEYS.get(role, [])
        for key in expected_keys:
            if key not in output:
                errors.append(f"필수 키 누락: {key}")

        return len(errors) == 0, errors

    def _generate_coaching(self, role: str, output: dict[str, Any], is_valid: bool) -> dict[str, Any]:
        """코칭 피드백 생성"""
        if not is_valid:
            return {
                "critique": "출력이 요구사항을 충족하지 않음",
                "encouragement": "다시 시도해보세요",
                "action": "retry",
            }

        # 역할별 코칭 피드백
        coaching_templates = {
            "ideator": {
                "critique": "아이디어 다양성 확인 필요",
                "encouragement": "발산적 사고 잘 수행됨",
                "action": "proceed",
            },
            "analyst": {
                "critique": "선별 기준 명확성 확인",
                "encouragement": "핵심 아이디어 잘 추출됨",
                "action": "proceed",
            },
            "critic": {
                "critique": "위험 분석 깊이 확인",
                "encouragement": "다각도 분석 완료",
                "action": "proceed",
            },
            "architect": {
                "critique": "모듈화 수준 확인",
                "encouragement": "설계 구조 적절함",
                "action": "proceed",
            },
            "executor": {
                "critique": "설계 준수 여부 확인",
                "encouragement": "구현 완료",
                "action": "proceed",
            },
            "validator": {
                "critique": "검증 범위 확인",
                "encouragement": "검증 완료",
                "action": "proceed",
            },
        }

        return coaching_templates.get(
            role,
            {
                "critique": "역할 수행 확인",
                "encouragement": "역할 완료",
                "action": "proceed",
            },
        )

    async def execute_parallel(
        self,
        session_id: str,
        roles: list[str],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, RoleOutput]:
        """
        독립적 역할 병렬 실행

        Args:
            session_id: 세션 ID
            roles: 병렬 실행할 역할 목록
            context: 공유 컨텍스트

        Returns:
            역할별 출력 딕셔너리
        """
        import asyncio

        tasks = [self.execute(session_id, role, context) for role in roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs = {}
        for role, result in zip(roles, results):
            if isinstance(result, Exception):
                outputs[role] = RoleOutput(
                    role=role,
                    status=RoleStatus.FAILED,
                    error=str(result),
                )
            else:
                outputs[role] = result

        return outputs
