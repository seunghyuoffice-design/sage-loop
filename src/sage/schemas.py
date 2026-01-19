"""
Sage API 스키마 - 요청/응답 모델 정의

세션 라이프사이클:
    pending → executing → waiting_approval → completed/failed
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════


class SessionStatus(str, Enum):
    """세션 상태"""

    PENDING = "pending"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    """실행 모드"""

    FULL_AUTO = "full-auto"
    PLAN_FIRST = "plan-first"
    INTERACTIVE = "interactive"


class ChainType(str, Enum):
    """체인 타입"""

    FULL = "FULL"
    QUICK = "QUICK"
    REVIEW = "REVIEW"
    DESIGN = "DESIGN"


class RoleStatus(str, Enum):
    """역할 실행 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ═══════════════════════════════════════════════════════════════
# Task Analysis
# ═══════════════════════════════════════════════════════════════


class TaskAnalysis(BaseModel):
    """작업 분석 결과"""

    task_type: str = Field(description="작업 유형 (신규/수정/검토)")
    complexity: str = Field(description="복잡도 (단순/중간/복잡)")
    risk: str = Field(description="위험도 (낮음/보통/높음)")
    matched_keywords: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Session
# ═══════════════════════════════════════════════════════════════


class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""

    user_request: str = Field(description="사용자 요청 텍스트")
    mode: Optional[ExecutionMode] = Field(default=None, description="실행 모드 (자동 선택 시 None)")
    chain_type: Optional[ChainType] = Field(default=None, description="체인 타입 (자동 선택 시 None)")


class SessionResponse(BaseModel):
    """세션 응답"""

    id: str = Field(description="세션 ID")
    status: SessionStatus
    mode: ExecutionMode
    chain_type: ChainType
    current_role: Optional[str] = None
    analysis: TaskAnalysis
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionResponse):
    """세션 상세 정보"""

    user_request: str
    completed_roles: list[str] = Field(default_factory=list)
    branch_count: int = 0
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Role Execution
# ═══════════════════════════════════════════════════════════════


class RoleOutput(BaseModel):
    """역할 출력"""

    role: str
    status: RoleStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[dict[str, Any]] = None
    coaching: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class ExecuteRequest(BaseModel):
    """체인 실행 요청"""

    force: bool = Field(default=False, description="승인 대기 무시하고 강제 실행")


class ExecuteResponse(BaseModel):
    """체인 실행 응답"""

    session_id: str
    status: SessionStatus
    checkpoint: Optional[str] = Field(default=None, description="현재 승인 대기 지점")
    message: str


# ═══════════════════════════════════════════════════════════════
# Approval
# ═══════════════════════════════════════════════════════════════


class ApproveRequest(BaseModel):
    """사용자 승인 요청"""

    approved: bool = Field(description="승인 여부")
    feedback: Optional[str] = Field(default=None, description="피드백 (거부 시)")


class ApproveResponse(BaseModel):
    """사용자 승인 응답"""

    session_id: str
    status: SessionStatus
    message: str


# ═══════════════════════════════════════════════════════════════
# Chain Definition
# ═══════════════════════════════════════════════════════════════


class BranchRule(BaseModel):
    """분기 규칙"""

    from_role: str = Field(alias="from")
    to_role: str = Field(alias="to")
    condition: str
    max_loops: int = 3

    model_config = {"populate_by_name": True}


class ChainDefinition(BaseModel):
    """체인 정의"""

    name: str
    roles: list[str]
    triggers: dict[str, list[str]]
    branches: list[BranchRule] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# SSE Events
# ═══════════════════════════════════════════════════════════════


class SSEEvent(BaseModel):
    """SSE 이벤트"""

    event_type: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any]


class SessionUpdateEvent(SSEEvent):
    """세션 업데이트 이벤트"""

    event_type: str = "session_update"


class RoleStartEvent(SSEEvent):
    """역할 시작 이벤트"""

    event_type: str = "role_start"
    role: str


class RoleCompleteEvent(SSEEvent):
    """역할 완료 이벤트"""

    event_type: str = "role_complete"
    role: str


class StallDetectedEvent(SSEEvent):
    """정체 감지 이벤트"""

    event_type: str = "stall_detected"
    current_role: str
    elapsed_seconds: float


# ═══════════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    """헬스체크 응답"""

    status: str  # healthy, degraded, unhealthy
    timestamp: str
    components: dict[str, str]
    active_sessions: int = 0
