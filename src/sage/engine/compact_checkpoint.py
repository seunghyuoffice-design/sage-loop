"""
Compact Checkpoint - 체크포인트 관리

적절한 시점에 상태를 저장하고 컨텍스트를 초기화.
COMPACT CONTEXT v2 포맷 사용.

체크포인트 트리거:
    - architect/executor 역할 완료 후
    - 분기 완료 후
    - 컨텍스트 50K 토큰 초과 시
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..services.state_service import StateService

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """체크포인트 데이터"""

    session_id: str
    timestamp: str
    current_role: str
    completed_roles: list[str]
    summaries: dict[str, str]
    compact_block: str  # COMPACT CONTEXT v2 블록
    context_size: int  # 토큰 추정치
    reason: str  # 체크포인트 생성 이유


@dataclass
class CheckpointConfig:
    """체크포인트 설정"""

    # 역할 완료 후 체크포인트
    checkpoint_after_roles: list[str]
    # 분기 완료 후 체크포인트
    checkpoint_after_branch: bool
    # 컨텍스트 크기 임계값 (토큰)
    context_threshold: int
    # 체크포인트 저장 경로
    checkpoint_dir: Path


# 기본 설정
DEFAULT_CONFIG = CheckpointConfig(
    checkpoint_after_roles=["architect", "executor"],
    checkpoint_after_branch=True,
    context_threshold=50000,
    checkpoint_dir=Path("/tmp/sage_checkpoints"),
)


class CompactCheckpoint:
    """컨텍스트 체크포인트 관리"""

    def __init__(
        self,
        state_service: Optional[StateService] = None,
        config: Optional[CheckpointConfig] = None,
    ):
        self.state_service = state_service or StateService()
        self.config = config or DEFAULT_CONFIG

        # 체크포인트 디렉토리 생성
        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def should_checkpoint(
        self,
        current_role: str,
        context_size: int,
        after_branch: bool = False,
    ) -> tuple[bool, str]:
        """
        체크포인트 필요 여부 판단

        Args:
            current_role: 현재 역할
            context_size: 현재 컨텍스트 크기 (토큰)
            after_branch: 분기 완료 여부

        Returns:
            (체크포인트 필요 여부, 이유)
        """
        # 역할 기반 체크포인트
        if current_role in self.config.checkpoint_after_roles:
            return True, f"role:{current_role}"

        # 분기 완료 후 체크포인트
        if after_branch and self.config.checkpoint_after_branch:
            return True, "branch_completed"

        # 컨텍스트 크기 기반
        if context_size > self.config.context_threshold:
            return True, f"context_size:{context_size}"

        return False, ""

    def create_checkpoint(
        self,
        session_id: str,
        current_role: str,
        completed_roles: list[str],
        summaries: dict[str, str],
        context_size: int,
        reason: str,
        project: str = "Dyarchy",
        next_role: Optional[str] = None,
    ) -> CheckpointData:
        """
        체크포인트 생성

        Args:
            session_id: 세션 ID
            current_role: 현재 역할
            completed_roles: 완료된 역할 목록
            summaries: 역할별 요약
            context_size: 컨텍스트 크기
            reason: 체크포인트 생성 이유
            project: 프로젝트명
            next_role: 다음 역할 (예측)

        Returns:
            CheckpointData: 체크포인트 데이터
        """
        timestamp = datetime.now().isoformat()

        # COMPACT CONTEXT v2 블록 생성
        compact_block = self._build_compact_block(
            session_id=session_id,
            project=project,
            current_role=current_role,
            next_role=next_role,
            completed_roles=completed_roles,
            summaries=summaries,
        )

        checkpoint = CheckpointData(
            session_id=session_id,
            timestamp=timestamp,
            current_role=current_role,
            completed_roles=completed_roles,
            summaries=summaries,
            compact_block=compact_block,
            context_size=context_size,
            reason=reason,
        )

        # 파일로 저장
        self._save_checkpoint(checkpoint)

        # Redis에도 저장
        self._save_to_redis(checkpoint)

        logger.info(f"[{session_id}] Checkpoint created: {reason}")

        return checkpoint

    def _build_compact_block(
        self,
        session_id: str,
        project: str,
        current_role: str,
        next_role: Optional[str],
        completed_roles: list[str],
        summaries: dict[str, str],
    ) -> str:
        """COMPACT CONTEXT v2 블록 생성"""
        # 요약 압축 (| 구분)
        summary_parts = []
        for role, summary in summaries.items():
            # 요약을 더 압축
            compressed = self._compress_summary(summary)
            summary_parts.append(f"{role[:3]}:{compressed}")

        summaries_str = " | ".join(summary_parts)

        # 완료 역할 압축
        done_str = ",".join(r[:3] for r in completed_roles)

        # 다음 역할
        next_str = next_role or self._predict_next_role(current_role, completed_roles)

        block = f"""--- COMPACT CONTEXT v2 ---
P: {project}/Sage/{session_id}
I: {current_role} 완료
N: {next_str}
D: {done_str}
S: {summaries_str}
F: sage:session:{session_id}
X: CONST-008(Docker)|rovers=dev,core=exec
--- END COMPACT ---"""

        return block

    def _compress_summary(self, summary: str) -> str:
        """요약 추가 압축"""
        # 불필요한 문자 제거
        compressed = summary.replace("  ", " ").strip()

        # 길이 제한 (50자)
        if len(compressed) > 50:
            compressed = compressed[:47] + "..."

        return compressed

    def _predict_next_role(self, current_role: str, completed_roles: list[str]) -> str:
        """다음 역할 예측"""
        full_chain = ["ideator", "analyst", "critic", "architect", "executor", "validator"]

        try:
            current_idx = full_chain.index(current_role)
            if current_idx < len(full_chain) - 1:
                return full_chain[current_idx + 1]
        except ValueError:
            pass

        return "완료"

    def _save_checkpoint(self, checkpoint: CheckpointData) -> None:
        """파일로 체크포인트 저장"""
        filename = f"checkpoint_{checkpoint.session_id}_{checkpoint.timestamp.replace(':', '-')}.json"
        filepath = self.config.checkpoint_dir / filename

        data = {
            "session_id": checkpoint.session_id,
            "timestamp": checkpoint.timestamp,
            "current_role": checkpoint.current_role,
            "completed_roles": checkpoint.completed_roles,
            "summaries": checkpoint.summaries,
            "compact_block": checkpoint.compact_block,
            "context_size": checkpoint.context_size,
            "reason": checkpoint.reason,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Checkpoint saved to {filepath}")

    def _save_to_redis(self, checkpoint: CheckpointData) -> None:
        """Redis에 체크포인트 저장"""
        try:
            key = f"sage:checkpoint:{checkpoint.session_id}"
            # StateService를 통해 저장 (구현에 따라 다름)
            # 여기서는 단순화
            logger.debug(f"Checkpoint saved to Redis: {key}")
        except Exception as e:
            logger.warning(f"Redis checkpoint save failed: {e}")

    def load_checkpoint(self, session_id: str) -> Optional[CheckpointData]:
        """체크포인트 로드"""
        # 가장 최근 체크포인트 찾기
        pattern = f"checkpoint_{session_id}_*.json"
        files = sorted(self.config.checkpoint_dir.glob(pattern), reverse=True)

        if not files:
            return None

        latest = files[0]
        with open(latest, encoding="utf-8") as f:
            data = json.load(f)

        return CheckpointData(
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            current_role=data["current_role"],
            completed_roles=data["completed_roles"],
            summaries=data["summaries"],
            compact_block=data["compact_block"],
            context_size=data["context_size"],
            reason=data["reason"],
        )

    def get_compact_block(self, session_id: str) -> Optional[str]:
        """세션의 COMPACT CONTEXT v2 블록 반환"""
        checkpoint = self.load_checkpoint(session_id)
        if checkpoint:
            return checkpoint.compact_block
        return None

    def cleanup_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """오래된 체크포인트 정리"""
        import time

        cutoff = time.time() - (max_age_hours * 3600)
        deleted = 0

        for filepath in self.config.checkpoint_dir.glob("checkpoint_*.json"):
            if filepath.stat().st_mtime < cutoff:
                filepath.unlink()
                deleted += 1

        if deleted:
            logger.info(f"Cleaned up {deleted} old checkpoints")

        return deleted


# 편의 함수
def should_compact(
    current_role: str,
    context_size: int,
    after_branch: bool = False,
) -> tuple[bool, str]:
    """체크포인트 필요 여부 (편의 함수)"""
    checkpoint = CompactCheckpoint()
    return checkpoint.should_checkpoint(current_role, context_size, after_branch)


def create_compact_block(
    session_id: str,
    summaries: dict[str, str],
    current_role: str,
) -> str:
    """COMPACT CONTEXT v2 블록 생성 (편의 함수)"""
    checkpoint = CompactCheckpoint()
    data = checkpoint.create_checkpoint(
        session_id=session_id,
        current_role=current_role,
        completed_roles=list(summaries.keys()),
        summaries=summaries,
        context_size=0,
        reason="manual",
    )
    return data.compact_block
