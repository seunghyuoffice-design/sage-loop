#!/usr/bin/env python3
"""
Sage Executor - /sage 스킬 호출 시 전체 체인 자동 실행

UserPromptSubmit Hook에서 호출되어:
1. 작업 분석
2. 체인 선택
3. 역할 순차 실행
4. 최종 결과 반환 (컨텍스트 주입)

컨텍스트 효율: Claude 왕복 없이 Python에서 모두 처리

v2: 파일 시스템 상태 동기화 추가 (stop-hook.sh 호환)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sage_loop.schemas import (
    ExecutionMode,
    SessionStatus,
    RoleStatus,
)
from sage_loop.services.state_service import StateService
from sage_loop.engine.chain_executor import ChainExecutor
from sage_loop.engine.role_runner import RoleRunner

# 파일 시스템 상태 경로 (stop-hook.sh와 호환)
STATE_DIR = Path(os.environ.get("SAGE_STATE_DIR", "/tmp"))


class FileStateSync:
    """파일 시스템 상태 동기화 (stop-hook.sh 호환)"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state_file = STATE_DIR / f"sage_session_{session_id}.json"

    def init_session(self, task: str, chain_type: str, chain_roles: list[str]) -> None:
        """세션 초기화"""
        state = {
            "session_id": self.session_id,
            "task": task,
            "chain_type": chain_type,
            "chain_roles": chain_roles,
            "current_role": None,
            "completed_roles": [],
            "role_outputs": {},
            "active": True,
            "exit_signal": False,
            "started_at": datetime.now().isoformat(),
            "loop_count": 0,
        }
        self._save(state)

    def start_role(self, role: str) -> None:
        """역할 시작"""
        state = self._load()
        state["current_role"] = role
        state["loop_count"] = state.get("loop_count", 0) + 1
        self._save(state)

    def complete_role(self, role: str, output: dict = None) -> None:
        """역할 완료"""
        state = self._load()

        if role not in state.get("completed_roles", []):
            state.setdefault("completed_roles", []).append(role)

        if output:
            state.setdefault("role_outputs", {})[role] = output

        # 다음 역할 확인
        chain_roles = state.get("chain_roles", [])
        completed = set(state.get("completed_roles", []))

        next_role = None
        for r in chain_roles:
            if r not in completed:
                next_role = r
                break

        state["current_role"] = next_role

        # 모든 역할 완료 시 exit_signal 설정
        if next_role is None:
            state["exit_signal"] = True
            state["exit_reason"] = "모든 역할 완료"
            state["completed_at"] = datetime.now().isoformat()

        self._save(state)

    def set_exit_signal(self, reason: str = "완료") -> None:
        """종료 신호 설정"""
        state = self._load()
        state["exit_signal"] = True
        state["exit_reason"] = reason
        state["active"] = False
        self._save(state)

    def cleanup(self) -> None:
        """세션 정리"""
        if self.state_file.exists():
            self.state_file.unlink()

    def _load(self) -> dict:
        """상태 로드"""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self, state: dict) -> None:
        """상태 저장"""
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))


class SageExecutor:
    """Sage 실행기 - 전체 체인 동기 실행"""

    def __init__(self):
        self.state_service = StateService()
        self.chain_executor = ChainExecutor(self.state_service)
        self.role_runner = RoleRunner(self.state_service)

    async def execute(self, user_request: str) -> dict:
        """
        전체 체인 실행

        Args:
            user_request: 사용자 요청

        Returns:
            실행 결과 (모든 역할 출력 포함)
        """
        result = {
            "success": False,
            "session_id": None,
            "chain_type": None,
            "mode": None,
            "roles_executed": [],
            "final_output": None,
            "error": None,
        }

        file_sync = None  # 파일 시스템 상태 동기화

        try:
            # 1. 작업 분석
            analysis = await self.chain_executor.analyze_task(user_request)

            # 2. 체인 선택
            chain_type = await self.chain_executor.select_chain(analysis)

            # 3. 모드 선택 (스크립트 실행은 항상 full-auto)
            mode = ExecutionMode.FULL_AUTO

            # 4. 세션 생성
            session = await self.state_service.create_session(
                user_request=user_request,
                chain_type=chain_type,
                mode=mode,
                analysis=analysis,
            )

            result["session_id"] = session.id
            result["chain_type"] = chain_type.value
            result["mode"] = mode.value
            result["analysis"] = {
                "task_type": analysis.task_type,
                "complexity": analysis.complexity,
                "risk": analysis.risk,
            }

            # 5. 체인 정의 조회
            chain_def = self.chain_executor._chains.get(chain_type)
            if not chain_def:
                raise ValueError(f"Chain not found: {chain_type}")

            roles = chain_def.get("roles", [])

            # 5.5. 파일 시스템 상태 초기화 (stop-hook.sh 호환)
            # 세션 ID를 환경 변수로 설정 (stop-hook.sh에서 사용)
            os.environ["SAGE_SESSION_ID"] = session.id
            file_sync = FileStateSync(session.id)
            file_sync.init_session(
                task=user_request,
                chain_type=chain_type.value,
                chain_roles=roles,
            )

            # 6. 역할 순차 실행
            await self.state_service.update_status(session.id, SessionStatus.EXECUTING)

            role_outputs = {}
            for role in roles:
                await self.state_service.update_current_role(session.id, role)

                # 파일 시스템 상태 동기화: 역할 시작
                file_sync.start_role(role)

                # 역할 실행
                output = await self.role_runner.execute(session.id, role)

                role_outputs[role] = {
                    "status": output.status.value,
                    "output": output.output,
                    "coaching": output.coaching,
                }
                result["roles_executed"].append(role)

                # 파일 시스템 상태 동기화: 역할 완료
                file_sync.complete_role(role, role_outputs[role])

                if output.status == RoleStatus.FAILED:
                    raise RuntimeError(f"Role {role} failed: {output.error}")

            # 7. 완료
            await self.state_service.update_status(session.id, SessionStatus.COMPLETED)

            # 파일 시스템 상태 동기화: 체인 완료
            file_sync.set_exit_signal("모든 역할 완료")

            result["success"] = True
            result["role_outputs"] = role_outputs
            result["final_output"] = role_outputs.get(roles[-1], {}).get("output")

        except Exception as e:
            result["error"] = str(e)
            if result["session_id"]:
                await self.state_service.update_status(
                    result["session_id"], SessionStatus.FAILED, error=str(e)
                )
            # 파일 시스템 상태 동기화: 오류로 종료
            if file_sync:
                file_sync.set_exit_signal(f"오류: {str(e)}")

        return result


def format_output(result: dict) -> str:
    """결과를 사람이 읽기 좋은 형식으로 포맷"""
    lines = []

    if result["success"]:
        lines.append("=" * 60)
        lines.append("SAGE 체인 실행 완료")
        lines.append("=" * 60)
        lines.append(f"세션: {result['session_id']}")
        lines.append(f"체인: {result['chain_type']}")
        lines.append(f"분석: {result.get('analysis', {})}")
        lines.append("")

        lines.append("실행된 역할:")
        for role in result["roles_executed"]:
            role_output = result.get("role_outputs", {}).get(role, {})
            status = role_output.get("status", "unknown")
            lines.append(f"  - {role}: {status}")

        lines.append("")
        lines.append("최종 출력:")
        final = result.get("final_output", {})
        lines.append(json.dumps(final, ensure_ascii=False, indent=2))

    else:
        lines.append("=" * 60)
        lines.append("SAGE 체인 실행 실패")
        lines.append("=" * 60)
        lines.append(f"에러: {result.get('error', 'Unknown error')}")

    return "\n".join(lines)


async def main():
    """메인 실행"""
    # stdin에서 요청 읽기
    input_data = json.loads(sys.stdin.read())
    user_prompt = input_data.get("user_prompt", "")

    # /sage 패턴 제거
    import re

    user_request = re.sub(r"^/sage\s*", "", user_prompt).strip()

    if not user_request:
        # 요청이 비어있으면 도움말 출력
        print(
            json.dumps(
                {
                    "result": "Sage 사용법: /sage <작업 설명>\n예: /sage 새로운 API 엔드포인트 개발"
                }
            )
        )
        return

    # 실행
    executor = SageExecutor()
    result = await executor.execute(user_request)

    # 결과 출력 (Claude 컨텍스트에 주입)
    formatted = format_output(result)
    print(json.dumps({"result": formatted}))


if __name__ == "__main__":
    asyncio.run(main())
