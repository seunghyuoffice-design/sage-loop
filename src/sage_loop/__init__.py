"""Sage Orchestrator - FastAPI 기반 역할 오케스트레이션 서비스"""

__version__ = "1.3.3"  # Cleanup: 사용되지 않는 파일 제거, 14단계 통합

# Claude Code Integration - YAML Export
from .engine.compact_checkpoint import (
    export_compact_yaml,
    restore_from_yaml,
    SageCompactState,
)

__all__ = [
    "export_compact_yaml",
    "restore_from_yaml",
    "SageCompactState",
]
