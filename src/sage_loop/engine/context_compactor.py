"""
Context Compactor - 역할 출력 압축기

역할 간 컨텍스트 전달 시 90% 이상 압축 목표.
전체 출력은 Redis에 저장하고, Sage에는 요약만 전달.

압축 전략:
    1. 역할별 요약 템플릿 적용
    2. 관사/조사 제거
    3. 약어 사용
    4. 핵심 정보만 추출
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class CompactedOutput:
    """압축된 역할 출력"""

    role: str
    summary: str  # 압축된 요약 (Sage 전달용)
    key_points: list[str]  # 핵심 포인트
    next_input_hint: str  # 다음 역할을 위한 힌트


# 역할별 요약 템플릿 (15단계 Full Chain)
SUMMARY_TEMPLATES = {
    "ideator": {
        "format": "아이디어 {count}개 | TOP: {top_items}",
        "extract": ["count", "top_items"],
    },
    "analyst": {
        "format": "선별 {selected}/{total} | 핵심: {key_items}",
        "extract": ["selected", "total", "key_items"],
    },
    "critic": {
        "format": "위험 {risk_level} | 이슈: {top_issues}",
        "extract": ["risk_level", "top_issues"],
    },
    "censor": {
        "format": "RULES {status} | 위반: {violations}",
        "extract": ["status", "violations"],
    },
    "academy": {
        "format": "근거 {evidence_count}개 | 참조: {references}",
        "extract": ["evidence_count", "references"],
    },
    "architect": {
        "format": "설계 {design_type} | 컴포넌트: {components}",
        "extract": ["design_type", "components"],
    },
    "left-state-councilor": {
        "format": "내정 {approval} | 의견: {opinion}",
        "extract": ["approval", "opinion"],
    },
    "right-state-councilor": {
        "format": "실무 {approval} | 의견: {opinion}",
        "extract": ["approval", "opinion"],
    },
    "executor": {
        "format": "실행 {status} | 파일: {files}",
        "extract": ["status", "files"],
    },
    "inspector": {
        "format": "감찰 {result} | 이슈: {issues}",
        "extract": ["result", "issues"],
    },
    "validator": {
        "format": "검증 {result} | 통과: {passed}/{total}",
        "extract": ["result", "passed", "total"],
    },
    "historian": {
        "format": "기록 {status} | 키: {session_key}",
        "extract": ["status", "session_key"],
    },
    "reflector": {
        "format": "교훈 {lessons_count}개 | 핵심: {key_lessons}",
        "extract": ["lessons_count", "key_lessons"],
    },
    "improver": {
        "format": "개선 {improvements_count}개 | 우선: {priority_items}",
        "extract": ["improvements_count", "priority_items"],
    },
    "feasibility-checker": {
        "format": "가능성 {feasibility} | 제약: {constraints}",
        "extract": ["feasibility", "constraints"],
    },
    "constraint-enforcer": {
        "format": "제약 {status} | 해결: {resolutions}",
        "extract": ["status", "resolutions"],
    },
}

# 역할별 필요한 이전 출력 (15단계 Full Chain)
ROLE_INPUT_REQUIREMENTS = {
    "ideator": [],
    "analyst": ["ideator"],
    "critic": ["analyst"],
    "censor": ["critic"],
    "academy": ["censor"],
    "architect": ["academy"],
    "left-state-councilor": ["architect"],
    "right-state-councilor": ["architect"],
    "executor": ["left-state-councilor", "right-state-councilor"],
    "inspector": ["executor"],
    "validator": ["inspector"],
    "historian": ["validator"],
    "reflector": ["historian"],
    "improver": ["reflector"],
    "feasibility-checker": ["analyst"],
    "constraint-enforcer": ["critic"],
}

# 압축 약어 매핑
ABBREVIATIONS = {
    "구현": "impl",
    "설정": "cfg",
    "함수": "fn",
    "디렉토리": "dir",
    "레포지토리": "repo",
    "파라미터": "param",
    "인증": "auth",
    "초기화": "init",
    "문서화": "doc",
    "개발": "dev",
    "프로덕션": "prod",
    "테스트": "test",
    "검증": "valid",
    "데이터베이스": "db",
    "인터페이스": "iface",
    "컨트롤러": "ctrl",
    "서비스": "svc",
    "컴포넌트": "comp",
}

# 제거할 조사/관사
REMOVE_PARTICLES = [
    "의 ",
    "을 ",
    "를 ",
    "이 ",
    "가 ",
    "에서 ",
    "으로 ",
    "로 ",
    "와 ",
    "과 ",
    "에 ",
    "는 ",
    "은 ",
]


class ContextCompactor:
    """컨텍스트 압축기 - 역할 간 정보 전달 최적화"""

    def __init__(self):
        self.templates = SUMMARY_TEMPLATES
        self.requirements = ROLE_INPUT_REQUIREMENTS
        self.abbreviations = ABBREVIATIONS

    def compact(self, role: str, output: dict[str, Any]) -> CompactedOutput:
        """
        역할 출력을 압축

        Args:
            role: 역할 이름
            output: 역할의 전체 출력 딕셔너리

        Returns:
            CompactedOutput: 압축된 출력
        """
        template = self.templates.get(role, {"format": "{output}", "extract": []})

        # 템플릿에서 필요한 값 추출
        extracted = self._extract_values(output, template["extract"])

        # 템플릿 적용
        try:
            summary = template["format"].format(**extracted)
        except KeyError:
            # 누락된 키가 있으면 원본 요약
            summary = self._fallback_summary(role, output)

        # 추가 압축 적용
        summary = self._apply_compression(summary)

        # 핵심 포인트 추출
        key_points = self._extract_key_points(output)

        # 다음 역할을 위한 힌트
        next_hint = self._generate_next_hint(role, extracted)

        return CompactedOutput(
            role=role,
            summary=summary,
            key_points=key_points,
            next_input_hint=next_hint,
        )

    def prepare_input(
        self,
        target_role: str,
        previous_outputs: dict[str, CompactedOutput],
    ) -> str:
        """
        다음 역할을 위한 입력 준비

        Args:
            target_role: 대상 역할
            previous_outputs: 이전 역할들의 압축된 출력

        Returns:
            str: 압축된 입력 문자열
        """
        required = self.requirements.get(target_role, [])

        if not required:
            return ""

        parts = []
        for prev_role in required:
            if prev_role in previous_outputs:
                output = previous_outputs[prev_role]
                parts.append(f"[{prev_role}] {output.summary}")
                if output.next_input_hint:
                    parts.append(f"  힌트: {output.next_input_hint}")

        return "\n".join(parts)

    def _extract_values(self, output: dict[str, Any], keys: list[str]) -> dict[str, Any]:
        """템플릿용 값 추출"""
        extracted = {}

        for key in keys:
            if key in output:
                value = output[key]
                # 리스트는 상위 3개만
                if isinstance(value, list):
                    value = ", ".join(str(v)[:30] for v in value[:3])
                    if len(output[key]) > 3:
                        value += f" 외 {len(output[key]) - 3}개"
                extracted[key] = value
            else:
                # 기본값
                extracted[key] = self._infer_value(key, output)

        return extracted

    def _infer_value(self, key: str, output: dict[str, Any]) -> str:
        """누락된 키의 값 추론"""
        # count 관련
        if "count" in key:
            for k, v in output.items():
                if isinstance(v, list):
                    return str(len(v))
            return "N/A"

        # 상태 관련
        if key in ["status", "result"]:
            if "error" in output:
                return "실패"
            return "완료"

        # 기본값
        return "N/A"

    def _fallback_summary(self, role: str, output: dict[str, Any]) -> str:
        """폴백 요약 생성"""
        # 출력에서 핵심 키 추출
        summary_parts = []

        if "status" in output:
            summary_parts.append(f"상태: {output['status']}")
        if "result" in output:
            summary_parts.append(f"결과: {output['result']}")
        if "error" in output:
            summary_parts.append(f"오류: {output['error']}")

        # 리스트 항목 개수
        for key, value in output.items():
            if isinstance(value, list) and len(value) > 0:
                summary_parts.append(f"{key}: {len(value)}개")

        return f"[{role}] " + " | ".join(summary_parts[:5])

    def _apply_compression(self, text: str) -> str:
        """텍스트 압축 적용"""
        result = text

        # 조사 제거
        for particle in REMOVE_PARTICLES:
            result = result.replace(particle, " ")

        # 약어 적용
        for full, abbr in self.abbreviations.items():
            result = result.replace(full, abbr)

        # 연속 공백 제거
        result = re.sub(r"\s+", " ", result).strip()

        return result

    def _extract_key_points(self, output: dict[str, Any]) -> list[str]:
        """핵심 포인트 추출"""
        points = []

        # 명시적 key_points
        if "key_points" in output:
            points.extend(output["key_points"][:5])

        # 결론/요약
        for key in ["conclusion", "summary", "recommendation"]:
            if key in output:
                points.append(str(output[key])[:100])

        # 경고/이슈
        for key in ["warnings", "issues", "risks"]:
            if key in output and output[key]:
                if isinstance(output[key], list):
                    points.extend(str(item)[:50] for item in output[key][:3])
                else:
                    points.append(str(output[key])[:100])

        return points[:5]  # 최대 5개

    def _generate_next_hint(self, role: str, extracted: dict[str, Any]) -> str:
        """다음 역할을 위한 힌트 생성"""
        hints = {
            "ideator": "아이디어 중 우선순위 평가 필요",
            "analyst": "선별된 항목에 대한 위험 분석 필요",
            "critic": "위험 요소 반영한 설계 필요",
            "architect": "설계대로 구현 필요",
            "executor": "구현 결과 검증 필요",
            "validator": "최종 검증 완료",
            "feasibility-checker": "가능성 결과 반영 필요",
            "constraint-enforcer": "제약 해결 후 진행",
        }
        return hints.get(role, "")

    def estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (대략)"""
        # 한글: 약 2자 = 1토큰
        # 영문: 약 4자 = 1토큰
        korean_chars = len(re.findall(r"[가-힣]", text))
        other_chars = len(text) - korean_chars

        return (korean_chars // 2) + (other_chars // 4)


# 편의 함수
def compact_output(role: str, output: dict[str, Any]) -> CompactedOutput:
    """역할 출력 압축 (편의 함수)"""
    compactor = ContextCompactor()
    return compactor.compact(role, output)


def prepare_role_input(target_role: str, previous_outputs: dict[str, CompactedOutput]) -> str:
    """역할 입력 준비 (편의 함수)"""
    compactor = ContextCompactor()
    return compactor.prepare_input(target_role, previous_outputs)
