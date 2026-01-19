"""
Role Dispatcher - 역할 라우팅 및 실행 디스패처

안건을 분석하여 적절한 Ministry/역할로 라우팅합니다.
"""

from dataclasses import dataclass
from enum import Enum

from .ministry_registry import (
    MinistryType,
    CouncilorType,
    MinistrySpec,
    RoleSpec,
    MINISTRY_REGISTRY,
    get_ministry_by_trigger,
)


class TaskType(Enum):
    """안건 유형"""

    INTERNAL = "internal"  # 내정 (좌의정)
    EXTERNAL = "external"  # 외정 (우의정)
    MIXED = "mixed"  # 복합


@dataclass
class TaskAnalysis:
    """안건 분석 결과"""

    task_type: TaskType
    primary_councilor: CouncilorType
    ministries: list[MinistrySpec]
    roles: list[RoleSpec]
    keywords: list[str]


class RoleDispatcher:
    """역할 디스패처"""

    # 내정 키워드 (좌의정 관할)
    INTERNAL_KEYWORDS = [
        "policy",
        "rules",
        "history",
        "log",
        "record",
        "resource",
        "gpu",
        "memory",
        "budget",
        "quality",
        "academic",
        "interpret",
        "compact",
        "session",
        "document",
    ]

    # 외정 키워드 (우의정 관할)
    EXTERNAL_KEYWORDS = [
        "implement",
        "execute",
        "code",
        "build",
        "deploy",
        "docker",
        "pipeline",
        "watchdog",
        "monitor",
        "compliance",
        "license",
        "security",
        "audit",
        "validate",
        "verify",
        "check",
        "test",
        "hook",
        "parallel",
        "sync",
        "route",
        "dashboard",
    ]

    def analyze_task(self, task_description: str) -> TaskAnalysis:
        """안건 분석"""
        task_lower = task_description.lower()

        # 키워드 매칭
        internal_matches = [k for k in self.INTERNAL_KEYWORDS if k in task_lower]
        external_matches = [k for k in self.EXTERNAL_KEYWORDS if k in task_lower]

        # 안건 유형 결정
        if internal_matches and external_matches:
            task_type = TaskType.MIXED
            primary_councilor = CouncilorType.RIGHT  # 외정 우선
        elif internal_matches:
            task_type = TaskType.INTERNAL
            primary_councilor = CouncilorType.LEFT
        else:
            task_type = TaskType.EXTERNAL
            primary_councilor = CouncilorType.RIGHT

        # 관련 Ministry 및 역할 찾기
        ministries = []
        roles = []
        keywords = internal_matches + external_matches

        for keyword in keywords:
            result = get_ministry_by_trigger(keyword)
            if result:
                ministry, role = result
                if ministry not in ministries:
                    ministries.append(ministry)
                if role not in roles:
                    roles.append(role)

        # 기본값: executor (외정 기본)
        if not roles:
            military = MINISTRY_REGISTRY[MinistryType.MILITARY]
            ministries = [military]
            roles = [r for r in military.roles if r.name == "executor"]

        return TaskAnalysis(
            task_type=task_type,
            primary_councilor=primary_councilor,
            ministries=ministries,
            roles=roles,
            keywords=keywords,
        )

    def get_execution_chain(self, analysis: TaskAnalysis) -> list[RoleSpec]:
        """실행 체인 생성 (역할 실행 순서)"""
        chain = []

        # 1. 실행 역할 (executor 등)
        execution_roles = [r for r in analysis.roles if r.model == "opus"]
        chain.extend(execution_roles)

        # 2. 검증 역할 (validator 등)
        validation_roles = [r for r in analysis.roles if r.name in ["validator", "compliance", "critic"]]
        chain.extend(validation_roles)

        # 3. 보조 역할
        other_roles = [r for r in analysis.roles if r not in execution_roles and r not in validation_roles]
        chain.extend(other_roles)

        return chain

    def format_dispatch_plan(self, task: str) -> str:
        """디스패치 계획 포맷"""
        analysis = self.analyze_task(task)
        chain = self.get_execution_chain(analysis)

        lines = [
            "## 안건 분석",
            f"- 유형: {analysis.task_type.value}",
            f"- 주관: {analysis.primary_councilor.value}",
            f"- 키워드: {', '.join(analysis.keywords) or '없음'}",
            "",
            "## 관할 Ministry",
        ]

        for ministry in analysis.ministries:
            lines.append(f"- {ministry.head.alias} ({ministry.type.value})")

        lines.extend(
            [
                "",
                "## 실행 체인",
            ]
        )

        for i, role in enumerate(chain, 1):
            lines.append(f"{i}. {role.alias} ({role.name}, {role.model})")

        return "\n".join(lines)


# 싱글톤 인스턴스
dispatcher = RoleDispatcher()
