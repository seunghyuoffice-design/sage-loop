"""
Sage FastAPI Server - 역할 오케스트레이션 API

엔드포인트:
- POST /sessions - 세션 생성
- GET /sessions/{id} - 세션 조회
- POST /sessions/{id}/execute - 체인 실행 시작
- POST /sessions/{id}/approve - 사용자 승인
- GET /sessions/{id}/stream - SSE 실시간 스트림
- GET /chains - 체인 정의 조회
- GET /health - 헬스체크
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import get_settings
from .schemas import (
    ApproveRequest,
    ApproveResponse,
    ChainDefinition,
    ChainType,
    CreateSessionRequest,
    ExecuteRequest,
    ExecuteResponse,
    HealthResponse,
    SessionDetail,
    SessionResponse,
    SessionStatus,
)
from .services.state_service import StateService
from .services.supervisor import Supervisor, get_supervisor
from .engine.chain_executor import ChainExecutor


# 모듈 레벨 인스턴스 (lifespan에서 초기화)
_state_service: StateService | None = None
_chain_executor: ChainExecutor | None = None
_supervisor: Supervisor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 초기화"""
    global _state_service, _chain_executor, _supervisor

    settings = get_settings()
    print(f"Sage API starting on port {settings.api_port}")
    print(f"Mode: {settings.mode}")

    # 인스턴스 초기화
    _state_service = StateService()
    _chain_executor = ChainExecutor(_state_service)
    _supervisor = get_supervisor()

    # 감독 루프 시작
    await _supervisor.start()
    print("Supervisor started")

    yield

    # 감독 루프 종료
    await _supervisor.stop()
    print("Sage API shutting down")


app = FastAPI(
    title="Sage API",
    description="Dyarchy 역할 오케스트레이션 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════════


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크"""
    components = {
        "state_service": "ready" if _state_service else "not_initialized",
        "chain_executor": "ready" if _chain_executor else "not_initialized",
        "supervisor": "ready" if _supervisor and _supervisor._running else "not_initialized",
    }

    status = "healthy" if all(v == "ready" for v in components.values()) else "degraded"
    active_sessions = await _state_service.count_active_sessions() if _state_service else 0

    return HealthResponse(
        status=status,
        timestamp=datetime.now().isoformat(),
        components=components,
        active_sessions=active_sessions,
    )


# ═══════════════════════════════════════════════════════════════
# Sessions
# ═══════════════════════════════════════════════════════════════


@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    새 Sage 세션 생성

    Request:
        {"user_request": "파이프라인 실패율 개선"}

    Response:
        {"id": "sess-001", "chain_type": "FULL", "mode": "plan-first", ...}
    """
    if not _state_service or not _chain_executor:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # 작업 분석
    analysis = await _chain_executor.analyze_task(request.user_request)

    # 체인 선택 (명시적 지정 또는 자동)
    chain_type = request.chain_type or await _chain_executor.select_chain(analysis)

    # 모드 선택 (명시적 지정 또는 자동)
    mode = request.mode or await _chain_executor.select_mode(request.user_request, analysis)

    # 세션 생성
    session = await _state_service.create_session(
        user_request=request.user_request,
        chain_type=chain_type,
        mode=mode,
        analysis=analysis,
    )

    return SessionResponse(
        id=session.id,
        status=session.status,
        mode=session.mode,
        chain_type=session.chain_type,
        current_role=session.current_role,
        analysis=analysis,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@app.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """세션 상태 조회"""
    if not _state_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    session = await _state_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@app.post("/sessions/{session_id}/execute", response_model=ExecuteResponse)
async def execute_session(session_id: str, request: ExecuteRequest = ExecuteRequest()):
    """
    체인 실행 시작

    plan-first 모드에서는 계획 승인 대기 상태로 전환
    full-auto 모드에서는 즉시 실행
    """
    if not _state_service or not _chain_executor:
        raise HTTPException(status_code=503, detail="Service not initialized")

    session = await _state_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status not in [SessionStatus.PENDING, SessionStatus.WAITING_APPROVAL]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute session in {session.status} state",
        )

    # plan-first 모드: 계획 승인 대기
    if session.mode.value == "plan-first" and not request.force:
        await _state_service.update_status(session_id, SessionStatus.WAITING_APPROVAL)
        return ExecuteResponse(
            session_id=session_id,
            status=SessionStatus.WAITING_APPROVAL,
            checkpoint="plan",
            message="계획 승인 대기 중. POST /sessions/{id}/approve로 승인하세요.",
        )

    # 실행 시작 (백그라운드)
    asyncio.create_task(_chain_executor.execute_chain(session_id))

    await _state_service.update_status(session_id, SessionStatus.EXECUTING)

    return ExecuteResponse(
        session_id=session_id,
        status=SessionStatus.EXECUTING,
        checkpoint=None,
        message="체인 실행 시작됨",
    )


@app.post("/sessions/{session_id}/approve", response_model=ApproveResponse)
async def approve_checkpoint(session_id: str, request: ApproveRequest):
    """
    사용자 승인

    approved=true: 실행 재개
    approved=false: 세션 취소
    """
    if not _state_service or not _chain_executor:
        raise HTTPException(status_code=503, detail="Service not initialized")

    session = await _state_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not waiting for approval (status: {session.status})",
        )

    if request.approved:
        # 실행 재개
        asyncio.create_task(_chain_executor.execute_chain(session_id))
        await _state_service.update_status(session_id, SessionStatus.EXECUTING)

        return ApproveResponse(
            session_id=session_id,
            status=SessionStatus.EXECUTING,
            message="승인됨. 체인 실행 재개.",
        )
    else:
        # 세션 취소
        await _state_service.update_status(session_id, SessionStatus.CANCELLED, error=request.feedback)

        return ApproveResponse(
            session_id=session_id,
            status=SessionStatus.CANCELLED,
            message=f"취소됨. 사유: {request.feedback or '없음'}",
        )


# ═══════════════════════════════════════════════════════════════
# SSE Stream
# ═══════════════════════════════════════════════════════════════


@app.get("/sessions/{session_id}/stream")
async def stream_session(session_id: str):
    """
    SSE 실시간 스트림

    세션의 상태 변경, 역할 시작/완료, 정체 감지 등을 실시간으로 스트리밍
    """
    if not _supervisor:
        raise HTTPException(status_code=503, detail="Supervisor not initialized")

    queue = _supervisor.subscribe()

    async def event_generator():
        try:
            # 초기 상태 전송
            if _state_service:
                session = await _state_service.get_session(session_id)
                if session:
                    yield f"data: {json.dumps({'type': 'initial', 'session': session.model_dump(mode='json')})}\n\n"

            # 이벤트 스트리밍
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 해당 세션의 이벤트만 전송
                    if data.get("session_id") == session_id:
                        yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # keepalive
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _supervisor.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ═══════════════════════════════════════════════════════════════
# Chain Definitions
# ═══════════════════════════════════════════════════════════════


@app.get("/chains", response_model=list[ChainDefinition])
async def get_chains():
    """체인 정의 조회"""
    if not _chain_executor:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return _chain_executor.get_chain_definitions()


@app.get("/chains/{chain_type}", response_model=ChainDefinition)
async def get_chain(chain_type: ChainType):
    """특정 체인 정의 조회"""
    if not _chain_executor:
        raise HTTPException(status_code=503, detail="Service not initialized")

    chain = _chain_executor.get_chain_definition(chain_type)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    return chain


# ═══════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════


def main():
    """CLI 진입점"""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.sage.api:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
