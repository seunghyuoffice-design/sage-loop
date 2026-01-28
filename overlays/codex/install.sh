#!/bin/bash
# Codex용 sage-loop 설치 스크립트

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

CODEX_DIR="$HOME/.codex"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    sage-loop Codex 설치 스크립트       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# 디렉토리 생성
mkdir -p "$CODEX_DIR"

# 1. config.toml 병합
echo -e "${YELLOW}► config.toml 설정 추가 중...${NC}"
if [ -f "$CODEX_DIR/config.toml" ]; then
    # 기존 설정에 추가
    if ! grep -q "agents.sage-loop" "$CODEX_DIR/config.toml"; then
        echo "" >> "$CODEX_DIR/config.toml"
        echo "# === sage-loop configuration ===" >> "$CODEX_DIR/config.toml"
        cat "$SCRIPT_DIR/config.toml" >> "$CODEX_DIR/config.toml"
        echo -e "  ${GREEN}✓ 설정 추가됨${NC}"
    else
        echo -e "  ${YELLOW}⚠ 이미 설정됨${NC}"
    fi
else
    cp "$SCRIPT_DIR/config.toml" "$CODEX_DIR/config.toml"
    echo -e "  ${GREEN}✓ 새 설정 생성됨${NC}"
fi

# 2. instructions.md 병합
echo -e "${YELLOW}► instructions.md 설정 추가 중...${NC}"
if [ -f "$CODEX_DIR/instructions.md" ]; then
    if ! grep -q "Sage Loop" "$CODEX_DIR/instructions.md"; then
        echo "" >> "$CODEX_DIR/instructions.md"
        cat "$SCRIPT_DIR/instructions.md" >> "$CODEX_DIR/instructions.md"
        echo -e "  ${GREEN}✓ 지침 추가됨${NC}"
    else
        echo -e "  ${YELLOW}⚠ 이미 설정됨${NC}"
    fi
else
    cp "$SCRIPT_DIR/instructions.md" "$CODEX_DIR/instructions.md"
    echo -e "  ${GREEN}✓ 새 지침 생성됨${NC}"
fi

# 3. Python 패키지 설치
echo -e "${YELLOW}► Python 패키지 설치 중...${NC}"
if [ -d "$REPO_ROOT" ] && [ -f "$REPO_ROOT/pyproject.toml" ]; then
    pip install -e "$REPO_ROOT" -q 2>/dev/null || pip install -e "$REPO_ROOT" 2>/dev/null || true
    echo -e "  ${GREEN}✓ sage-loop 패키지 설치됨${NC}"
fi

# 4. CLI 확인
echo -e "${YELLOW}► CLI 확인 중...${NC}"
if command -v sage-orchestrator &> /dev/null; then
    echo -e "  ${GREEN}✓ sage-orchestrator 사용 가능${NC}"
else
    echo -e "  ${YELLOW}⚠ PATH에 추가 필요: pip install -e .${NC}"
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✓ Codex 설치 완료!            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "사용법:"
echo -e "  ${BLUE}/sage \"작업 내용\"${NC}               # 대화에서 입력"
echo -e "  ${BLUE}sage-orchestrator \"작업\"${NC}        # CLI 직접 실행"
echo -e "  ${BLUE}sage-orchestrator --status${NC}       # 상태 확인"
echo
echo -e "설정 파일:"
echo -e "  ${BLUE}$CODEX_DIR/config.toml${NC}"
echo -e "  ${BLUE}$CODEX_DIR/instructions.md${NC}"
