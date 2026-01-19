"""
Ministry Registry - 의정부 6조 역할 등록부

Ministry 역할의 자동 실행을 위한 기반 구조.
각 Ministry의 역할, 권한, 모델 정보를 정의합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MinistryType(Enum):
    """의정부 6조 분류"""

    # 내정 (좌의정 관할)
    PERSONNEL = "ministry-personnel"  # 이조 - 인사
    FINANCE = "ministry-finance"  # 호조 - 재정
    RITES = "ministry-rites"  # 예조 - 예법

    # 외정 (우의정 관할)
    MILITARY = "ministry-military"  # 병조 - 실행
    JUSTICE = "ministry-justice"  # 형조 - 검증
    WORKS = "ministry-works"  # 공조 - 인프라


class CouncilorType(Enum):
    """의정 분류"""

    LEFT = "left-state-councilor"  # 좌의정 - 내정
    RIGHT = "right-state-councilor"  # 우의정 - 외정


@dataclass
class RoleSpec:
    """역할 명세"""

    name: str
    alias: str  # 한글명
    model: str  # haiku, sonnet, opus
    description: str
    allowed_tools: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)


@dataclass
class MinistrySpec:
    """Ministry 명세"""

    type: MinistryType
    councilor: CouncilorType
    head: RoleSpec  # 판서
    roles: list[RoleSpec]  # 하위 역할


# 의정부 6조 등록부
MINISTRY_REGISTRY: dict[MinistryType, MinistrySpec] = {
    # ═══════════════════════════════════════════
    # 내정 3조 (좌의정 관할)
    # ═══════════════════════════════════════════
    MinistryType.PERSONNEL: MinistrySpec(
        type=MinistryType.PERSONNEL,
        councilor=CouncilorType.LEFT,
        head=RoleSpec(
            name="ministry-personnel",
            alias="이조판서",
            model="sonnet",
            description="인사/역할 관리",
        ),
        roles=[
            RoleSpec(
                name="policy-keeper",
                alias="정책 관리자",
                model="haiku",
                description="RULES 정책 관리 및 업데이트",
                triggers=["policy", "rules", "regulation"],
            ),
            RoleSpec(
                name="historian",
                alias="사관",
                model="haiku",
                description="역할 결정 히스토리 기록",
                triggers=["history", "log", "record"],
            ),
        ],
    ),
    MinistryType.FINANCE: MinistrySpec(
        type=MinistryType.FINANCE,
        councilor=CouncilorType.LEFT,
        head=RoleSpec(
            name="ministry-finance",
            alias="호조판서",
            model="sonnet",
            description="재정/자원 관리",
        ),
        roles=[
            RoleSpec(
                name="resource-manager",
                alias="자원 관리자",
                model="sonnet",
                description="GPU/메모리/CPU 예산 관리",
                triggers=["resource", "gpu", "memory", "budget"],
            ),
            RoleSpec(
                name="quality",
                alias="품질 관리자",
                model="sonnet",
                description="학습 데이터 품질 검증",
                triggers=["quality", "data", "validation"],
            ),
        ],
    ),
    MinistryType.RITES: MinistrySpec(
        type=MinistryType.RITES,
        councilor=CouncilorType.LEFT,
        head=RoleSpec(
            name="ministry-rites",
            alias="예조판서",
            model="sonnet",
            description="예법/문서 관리",
        ),
        roles=[
            RoleSpec(
                name="academy",
                alias="홍문관",
                model="sonnet",
                description="학술 자문과 RULES 해석",
                triggers=["academic", "interpret", "consult"],
            ),
            RoleSpec(
                name="compact",
                alias="압축 담당",
                model="haiku",
                description="대화 히스토리 압축",
                triggers=["compact", "compress", "context"],
            ),
            RoleSpec(
                name="session",
                alias="세션 관리자",
                model="haiku",
                description="세션 상태 파싱/복원",
                triggers=["session", "state", "restore"],
            ),
        ],
    ),
    # ═══════════════════════════════════════════
    # 외정 3조 (우의정 관할)
    # ═══════════════════════════════════════════
    MinistryType.MILITARY: MinistrySpec(
        type=MinistryType.MILITARY,
        councilor=CouncilorType.RIGHT,
        head=RoleSpec(
            name="ministry-military",
            alias="병조판서",
            model="sonnet",
            description="실행/운영 관리",
        ),
        roles=[
            RoleSpec(
                name="executor",
                alias="실행자",
                model="opus",
                description="Architect 설계를 그대로 구현",
                allowed_tools=["Read", "Write", "Edit", "Bash"],
                triggers=["implement", "execute", "code", "build"],
            ),
            RoleSpec(
                name="deploy",
                alias="배포 담당",
                model="haiku",
                description="Docker 이미지 빌드/배포",
                triggers=["deploy", "docker", "release"],
            ),
            RoleSpec(
                name="pipeline",
                alias="파이프라인 담당",
                model="haiku",
                description="파이프라인 관리 (시작/중지/상태)",
                triggers=["pipeline", "start", "stop", "status"],
            ),
            RoleSpec(
                name="watchdog",
                alias="감시자",
                model="haiku",
                description="Core 프리징 감지, 재시작 트리거",
                triggers=["watchdog", "monitor", "freeze", "restart"],
            ),
        ],
    ),
    MinistryType.JUSTICE: MinistrySpec(
        type=MinistryType.JUSTICE,
        councilor=CouncilorType.RIGHT,
        head=RoleSpec(
            name="ministry-justice",
            alias="형조판서",
            model="opus",
            description="검증/감사 관리",
        ),
        roles=[
            RoleSpec(
                name="compliance",
                alias="컴플라이언스",
                model="sonnet",
                description="라이선스/아키텍처/보안 검증",
                triggers=["compliance", "license", "security", "audit"],
            ),
            RoleSpec(
                name="critic",
                alias="사헌부",
                model="opus",
                description="사후 감찰과 탄핵",
                triggers=["critic", "review", "inspect"],
            ),
            RoleSpec(
                name="validator",
                alias="검증자",
                model="sonnet",
                description="출력 품질/스키마 검증",
                triggers=["validate", "verify", "check"],
            ),
            RoleSpec(
                name="censor-general",
                alias="사간원",
                model="sonnet",
                description="사전 간쟁/봉박",
                triggers=["censor", "block", "prevent"],
            ),
            RoleSpec(
                name="constraint-enforcer",
                alias="제약 강제자",
                model="sonnet",
                description="제약 조건 강제",
                triggers=["constraint", "enforce", "rule"],
            ),
        ],
    ),
    MinistryType.WORKS: MinistrySpec(
        type=MinistryType.WORKS,
        councilor=CouncilorType.RIGHT,
        head=RoleSpec(
            name="ministry-works",
            alias="공조판서",
            model="sonnet",
            description="인프라/빌드 관리",
        ),
        roles=[
            RoleSpec(
                name="hooks",
                alias="훅 관리자",
                model="haiku",
                description="Claude Code Hook 관리",
                triggers=["hook", "automation", "workflow"],
            ),
            RoleSpec(
                name="parallel",
                alias="병렬 담당",
                model="haiku",
                description="Git worktree 병렬 작업",
                triggers=["parallel", "worktree", "concurrent"],
            ),
            RoleSpec(
                name="sync",
                alias="동기화 담당",
                model="haiku",
                description="rovers→core/forge 파일 동기화",
                triggers=["sync", "synchronize", "transfer"],
            ),
            RoleSpec(
                name="route",
                alias="라우팅 담당",
                model="haiku",
                description="서버 라우팅/동기화 상태 확인",
                triggers=["route", "routing", "network"],
            ),
            RoleSpec(
                name="dash",
                alias="대시보드",
                model="haiku",
                description="통합 대시보드",
                triggers=["dashboard", "monitor", "status"],
            ),
        ],
    ),
}


def get_ministry_by_trigger(trigger: str) -> Optional[tuple[MinistrySpec, RoleSpec]]:
    """트리거 키워드로 적절한 Ministry와 역할 찾기"""
    trigger_lower = trigger.lower()

    for ministry in MINISTRY_REGISTRY.values():
        for role in ministry.roles:
            if any(t in trigger_lower for t in role.triggers):
                return ministry, role

    return None


def get_councilor_ministries(councilor: CouncilorType) -> list[MinistrySpec]:
    """의정 관할 Ministry 목록"""
    return [m for m in MINISTRY_REGISTRY.values() if m.councilor == councilor]


def get_all_roles() -> list[RoleSpec]:
    """모든 역할 목록"""
    roles = []
    for ministry in MINISTRY_REGISTRY.values():
        roles.append(ministry.head)
        roles.extend(ministry.roles)
    return roles
