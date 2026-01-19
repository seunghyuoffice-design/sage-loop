#!/usr/bin/env python3
"""
Sage MCP Server - Claude Code 스킬 통합

MCP 툴:
    - sage_create_session: 세션 생성 (체인/모드 자동 선택)
    - sage_get_session: 세션 상태 조회
    - sage_execute: 체인 실행
    - sage_approve: 사용자 승인
    - sage_get_chains: 체인 정의 조회

사용법:
    Claude Code에서 자동으로 Tool로 사용 가능
"""

import asyncio
import json
import sys
from typing import Any

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Sage 모듈 (상대 경로)
from .schemas import (
    ChainType,
    ExecutionMode,
    SessionStatus,
)
from .services.state_service import StateService
from .engine.chain_executor import ChainExecutor

# 서버 인스턴스
server = Server("sage-orchestrator")

# 서비스 인스턴스 (lazy init)
_state_service: StateService | None = None
_chain_executor: ChainExecutor | None = None


def get_services():
    """서비스 인스턴스 반환"""
    global _state_service, _chain_executor
    if _state_service is None:
        _state_service = StateService()
        _chain_executor = ChainExecutor(_state_service)
    return _state_service, _chain_executor


# ═══════════════════════════════════════════════════════════════
# Tool Definitions
# ═══════════════════════════════════════════════════════════════


@server.list_tools()
async def list_tools() -> list[Tool]:
    """사용 가능한 도구 목록"""
    return [
        Tool(
            name="sage_create_session",
            description="Sage 세션 생성. 작업 분석 후 적절한 체인과 모드 자동 선택.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "사용자 요청 텍스트 (예: '새로운 기능 개발', '버그 수정')",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["full-auto", "plan-first", "interactive"],
                        "description": "실행 모드 (선택, 기본: 자동 선택)",
                    },
                    "chain_type": {
                        "type": "string",
                        "enum": ["FULL", "QUICK", "REVIEW", "DESIGN"],
                        "description": "체인 타입 (선택, 기본: 자동 선택)",
                    },
                },
                "required": ["user_request"],
            },
        ),
        Tool(
            name="sage_get_session",
            description="Sage 세션 상태 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "세션 ID",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="sage_execute",
            description="체인 실행 시작. plan-first 모드에서는 승인 대기 상태로 전환.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "세션 ID",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "승인 대기 무시하고 강제 실행 (기본: false)",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="sage_approve",
            description="사용자 승인. 승인 시 실행 재개, 거부 시 세션 취소.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "세션 ID",
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "승인 여부",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "피드백 (거부 시 사유)",
                    },
                },
                "required": ["session_id", "approved"],
            },
        ),
        Tool(
            name="sage_get_chains",
            description="사용 가능한 체인 정의 조회",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sage_get_role_output",
            description="특정 역할의 출력 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "세션 ID",
                    },
                    "role": {
                        "type": "string",
                        "description": "역할 이름 (ideator, analyst, critic, architect, executor, validator)",
                    },
                },
                "required": ["session_id", "role"],
            },
        ),
    ]


# ═══════════════════════════════════════════════════════════════
# Tool Handlers
# ═══════════════════════════════════════════════════════════════


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """도구 실행"""
    state_service, chain_executor = get_services()

    try:
        if name == "sage_create_session":
            result = await _create_session(state_service, chain_executor, arguments)

        elif name == "sage_get_session":
            result = await _get_session(state_service, arguments)

        elif name == "sage_execute":
            result = await _execute_chain(state_service, chain_executor, arguments)

        elif name == "sage_approve":
            result = await _approve(state_service, chain_executor, arguments)

        elif name == "sage_get_chains":
            result = await _get_chains(chain_executor)

        elif name == "sage_get_role_output":
            result = await _get_role_output(state_service, arguments)

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def _create_session(
    state_service: StateService,
    chain_executor: ChainExecutor,
    args: dict,
) -> dict:
    """세션 생성"""
    user_request = args["user_request"]

    # 작업 분석
    analysis = await chain_executor.analyze_task(user_request)

    # 체인 선택
    chain_type_str = args.get("chain_type")
    if chain_type_str:
        chain_type = ChainType(chain_type_str)
    else:
        chain_type = await chain_executor.select_chain(analysis)

    # 모드 선택
    mode_str = args.get("mode")
    if mode_str:
        mode = ExecutionMode(mode_str)
    else:
        mode = await chain_executor.select_mode(user_request, analysis)

    # 세션 생성
    session = await state_service.create_session(
        user_request=user_request,
        chain_type=chain_type,
        mode=mode,
        analysis=analysis,
    )

    return {
        "session_id": session.id,
        "status": session.status.value,
        "chain_type": session.chain_type.value,
        "mode": session.mode.value,
        "analysis": {
            "task_type": analysis.task_type,
            "complexity": analysis.complexity,
            "risk": analysis.risk,
            "matched_keywords": analysis.matched_keywords,
        },
        "message": f"세션 생성 완료. 체인: {chain_type.value}, 모드: {mode.value}",
    }


async def _get_session(state_service: StateService, args: dict) -> dict:
    """세션 조회"""
    session_id = args["session_id"]
    session = await state_service.get_session(session_id)

    if not session:
        return {"error": f"Session not found: {session_id}"}

    return {
        "session_id": session.id,
        "status": session.status.value,
        "chain_type": session.chain_type.value,
        "mode": session.mode.value,
        "current_role": session.current_role,
        "completed_roles": session.completed_roles,
        "branch_count": session.branch_count,
        "error": session.error,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


async def _execute_chain(
    state_service: StateService,
    chain_executor: ChainExecutor,
    args: dict,
) -> dict:
    """체인 실행"""
    session_id = args["session_id"]
    force = args.get("force", False)

    session = await state_service.get_session(session_id)
    if not session:
        return {"error": f"Session not found: {session_id}"}

    if session.status not in [SessionStatus.PENDING, SessionStatus.WAITING_APPROVAL]:
        return {"error": f"Cannot execute session in {session.status.value} state"}

    # plan-first 모드: 승인 대기
    if session.mode == ExecutionMode.PLAN_FIRST and not force:
        await state_service.update_status(session_id, SessionStatus.WAITING_APPROVAL)
        return {
            "session_id": session_id,
            "status": "waiting_approval",
            "checkpoint": "plan",
            "message": "계획 승인 대기 중. sage_approve로 승인하세요.",
        }

    # 실행 시작 (백그라운드)
    asyncio.create_task(chain_executor.execute_chain(session_id))
    await state_service.update_status(session_id, SessionStatus.EXECUTING)

    return {
        "session_id": session_id,
        "status": "executing",
        "message": "체인 실행 시작됨",
    }


async def _approve(
    state_service: StateService,
    chain_executor: ChainExecutor,
    args: dict,
) -> dict:
    """사용자 승인"""
    session_id = args["session_id"]
    approved = args["approved"]
    feedback = args.get("feedback")

    session = await state_service.get_session(session_id)
    if not session:
        return {"error": f"Session not found: {session_id}"}

    if session.status != SessionStatus.WAITING_APPROVAL:
        return {"error": f"Session is not waiting for approval (status: {session.status.value})"}

    if approved:
        asyncio.create_task(chain_executor.execute_chain(session_id))
        await state_service.update_status(session_id, SessionStatus.EXECUTING)
        return {
            "session_id": session_id,
            "status": "executing",
            "message": "승인됨. 체인 실행 재개.",
        }
    else:
        await state_service.update_status(session_id, SessionStatus.CANCELLED, error=feedback)
        return {
            "session_id": session_id,
            "status": "cancelled",
            "message": f"취소됨. 사유: {feedback or '없음'}",
        }


async def _get_chains(chain_executor: ChainExecutor) -> dict:
    """체인 정의 조회"""
    definitions = chain_executor.get_chain_definitions()

    return {
        "chains": [
            {
                "name": d.name,
                "roles": d.roles,
                "triggers": d.triggers,
            }
            for d in definitions
        ]
    }


async def _get_role_output(state_service: StateService, args: dict) -> dict:
    """역할 출력 조회"""
    session_id = args["session_id"]
    role = args["role"]

    output = await state_service.get_role_output(session_id, role)
    if not output:
        return {"error": f"No output found for role {role} in session {session_id}"}

    return {
        "role": output.role,
        "status": output.status.value,
        "output": output.output,
        "coaching": output.coaching,
        "completed_at": output.completed_at.isoformat() if output.completed_at else None,
    }


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════


async def main():
    """MCP 서버 실행"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
