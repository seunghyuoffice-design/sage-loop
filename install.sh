#!/bin/bash
# sage-loop 원클릭 설치 스크립트
# Usage: curl -fsSL https://raw.githubusercontent.com/seunghyuoffice-design/sage-loop/main/install.sh | bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       sage-loop 설치 스크립트          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# 플랫폼 자동 감지
detect_platform() {
    if [ -d "$HOME/.claude" ] || command -v claude &> /dev/null; then
        echo "claude"
    elif [ -d "$HOME/.codex" ] || command -v codex &> /dev/null; then
        echo "codex"
    else
        echo "claude"  # 기본값
    fi
}

PLATFORM="${1:-$(detect_platform)}"
echo -e "${YELLOW}► 플랫폼: ${PLATFORM}${NC}"

# 임시 디렉토리 생성
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 레포지토리 클론
echo -e "${YELLOW}► 레포지토리 다운로드 중...${NC}"
git clone --depth 1 --quiet https://github.com/seunghyuoffice-design/sage-loop.git "$TEMP_DIR/sage-loop"
cd "$TEMP_DIR/sage-loop"

# Python 패키지 설치 (선택사항)
if command -v pip &> /dev/null; then
    echo -e "${YELLOW}► Python 패키지 설치 중...${NC}"
    pip install -e . --quiet 2>/dev/null || pip install -e . -q 2>/dev/null || true
fi

# 플랫폼별 설정
echo -e "${YELLOW}► ${PLATFORM} 오버레이 적용 중...${NC}"
python3 scripts/apply_overlay.py "$PLATFORM" -q

# Claude Code 전용: hooks 복사
if [ "$PLATFORM" = "claude" ]; then
    HOOKS_DIR="$HOME/.claude/hooks"
    mkdir -p "$HOOKS_DIR"

    echo -e "${YELLOW}► Hooks 설치 중...${NC}"
    cp hooks/*.py "$HOOKS_DIR/" 2>/dev/null || true
    cp hooks/*.sh "$HOOKS_DIR/" 2>/dev/null || true
    chmod +x "$HOOKS_DIR"/*.sh 2>/dev/null || true
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✓ 설치 완료!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "사용법:"
if [ "$PLATFORM" = "claude" ]; then
    echo -e "  ${BLUE}/sage \"작업 내용\"${NC}           # Sage Loop 시작"
    echo -e "  ${BLUE}/sage --chain quick \"버그 수정\"${NC}  # Quick 체인"
else
    echo -e "  ${BLUE}sage-orchestrator \"작업 내용\"${NC}"
fi
echo
echo -e "문서: https://github.com/seunghyuoffice-design/sage-loop"
