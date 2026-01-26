"""Sage Orchestrator - FastAPI 기반 역할 오케스트레이션 서비스"""

__version__ = "1.2.0"  # 환경 하드코딩 제거, 코드 품질 개선

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
