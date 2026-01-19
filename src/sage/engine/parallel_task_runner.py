"""
Parallel Task Runner - 병렬 Task 실행기

독립적인 역할을 병렬로 실행하여 처리 시간 단축.
각 역할은 별도 Task로 실행되어 컨텍스트 격리.

병렬 실행 가능한 그룹:
    - verification: feasibility-checker, constraint-enforcer
    - validation: tester, validator
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..services.state_service import StateService
from .context_compactor import CompactedOutput, ContextCompactor
from .task_dispatcher import TaskDispatcher, TaskResult

logger = logging.getLogger(__name__)


@dataclass
class ParallelResult:
    """병렬 실행 결과"""

    group_name: str
    results: dict[str, TaskResult]  # 역할 → 결과
    total_time_ms: int
    success_count: int
    failure_count: int


# 병렬 실행 가능한 역할 그룹
PARALLEL_GROUPS = {
    # 분기 역할 병렬화
    "verification": {
        "roles": ["feasibility-checker", "constraint-enforcer"],
        "description": "가능성 및 제약 동시 검증",
        "trigger_after": ["analyst", "critic"],
    },
    # 검증 역할 병렬화
    "validation": {
        "roles": ["tester", "validator"],
        "description": "테스트 및 검증 동시 실행",
        "trigger_after": ["executor"],
    },
    # 분석 역할 병렬화 (선택적)
    "analysis": {
        "roles": ["analyst", "critic"],
        "description": "분석 및 비판 동시 실행",
        "trigger_after": ["ideator"],
        "experimental": True,
    },
}


class ParallelTaskRunner:
    """병렬 Task 실행기"""

    def __init__(self, state_service: Optional[StateService] = None):
        self.state_service = state_service or StateService()
        self.dispatcher = TaskDispatcher(self.state_service)
        self.compactor = ContextCompactor()
        self.groups = PARALLEL_GROUPS

    async def execute_parallel(
        self,
        session_id: str,
        roles: list[str],
        user_request: str,
        previous_outputs: dict[str, CompactedOutput],
    ) -> ParallelResult:
        """
        독립적 역할 병렬 실행

        각 역할은 별도 Task로 실행 (컨텍스트 격리)

        Args:
            session_id: 세션 ID
            roles: 병렬 실행할 역할 목록
            user_request: 원본 사용자 요청
            previous_outputs: 이전 역할들의 압축된 출력

        Returns:
            ParallelResult: 병렬 실행 결과
        """
        start_time = datetime.now()
        logger.info(f"[{session_id}] Starting parallel execution: {roles}")

        # 병렬 Task 생성
        tasks = [self._execute_single(session_id, role, user_request, previous_outputs) for role in roles]

        # 동시 실행 (예외 포함)
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 정리
        results: dict[str, TaskResult] = {}
        success_count = 0
        failure_count = 0

        for role, result in zip(roles, results_list):
            if isinstance(result, Exception):
                logger.error(f"[{session_id}] Parallel task {role} failed: {result}")
                results[role] = TaskResult(
                    role=role,
                    status="failed",
                    output={},
                    summary=f"실행 오류: {str(result)}",
                    redis_key=f"sage:role:{session_id}:{role}",
                    started_at=start_time.isoformat(),
                    completed_at=datetime.now().isoformat(),
                    error=str(result),
                )
                failure_count += 1
            else:
                results[role] = result
                if result.status == "completed":
                    success_count += 1
                else:
                    failure_count += 1

        end_time = datetime.now()
        total_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{session_id}] Parallel execution completed: "
            f"{success_count} success, {failure_count} failures, {total_time_ms}ms"
        )

        return ParallelResult(
            group_name=self._find_group_name(roles),
            results=results,
            total_time_ms=total_time_ms,
            success_count=success_count,
            failure_count=failure_count,
        )

    async def _execute_single(
        self,
        session_id: str,
        role: str,
        user_request: str,
        previous_outputs: dict[str, CompactedOutput],
    ) -> TaskResult:
        """단일 역할 실행"""
        return await self.dispatcher.dispatch(
            session_id=session_id,
            role=role,
            user_request=user_request,
            previous_outputs=previous_outputs,
        )

    def _find_group_name(self, roles: list[str]) -> str:
        """역할 목록에 해당하는 그룹 이름 찾기"""
        role_set = set(roles)
        for group_name, group_def in self.groups.items():
            if set(group_def["roles"]) == role_set:
                return group_name
        return "custom"

    def get_parallel_group(self, trigger_role: str) -> Optional[list[str]]:
        """
        트리거 역할 완료 후 병렬 실행 가능한 역할 목록 반환

        Args:
            trigger_role: 완료된 역할

        Returns:
            병렬 실행 가능한 역할 목록 (없으면 None)
        """
        for group_name, group_def in self.groups.items():
            # 실험적 그룹 제외
            if group_def.get("experimental"):
                continue

            if trigger_role in group_def.get("trigger_after", []):
                return group_def["roles"]

        return None

    def can_parallelize(self, roles: list[str]) -> bool:
        """
        주어진 역할들이 병렬 실행 가능한지 확인

        Args:
            roles: 역할 목록

        Returns:
            병렬 실행 가능 여부
        """
        role_set = set(roles)

        for group_def in self.groups.values():
            if set(group_def["roles"]) == role_set:
                return not group_def.get("experimental", False)

        return False

    async def execute_group(
        self,
        session_id: str,
        group_name: str,
        user_request: str,
        previous_outputs: dict[str, CompactedOutput],
    ) -> ParallelResult:
        """
        그룹 이름으로 병렬 실행

        Args:
            session_id: 세션 ID
            group_name: 그룹 이름 (verification, validation 등)
            user_request: 원본 사용자 요청
            previous_outputs: 이전 역할들의 압축된 출력

        Returns:
            ParallelResult: 병렬 실행 결과
        """
        if group_name not in self.groups:
            raise ValueError(f"Unknown group: {group_name}")

        group_def = self.groups[group_name]
        roles = group_def["roles"]

        return await self.execute_parallel(
            session_id=session_id,
            roles=roles,
            user_request=user_request,
            previous_outputs=previous_outputs,
        )


# 편의 함수
async def run_parallel_tasks(
    session_id: str,
    roles: list[str],
    user_request: str,
    previous_outputs: dict[str, CompactedOutput],
) -> ParallelResult:
    """병렬 Task 실행 (편의 함수)"""
    runner = ParallelTaskRunner()
    return await runner.execute_parallel(session_id, roles, user_request, previous_outputs)


def get_parallel_roles_for(trigger_role: str) -> Optional[list[str]]:
    """트리거 역할에 대한 병렬 실행 가능 역할 (편의 함수)"""
    runner = ParallelTaskRunner()
    return runner.get_parallel_group(trigger_role)
