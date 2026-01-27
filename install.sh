#!/bin/bash
# sage-loop 원클릭 설치 스크립트
# Usage: curl -fsSL https://raw.githubusercontent.com/seunghyuoffice-design/sage-loop/main/install.sh | bash
# Platforms: claude, codex, antigravity, opencode, cursor, vscode

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
    elif [ -d "$HOME/.gemini/antigravity" ]; then
        echo "antigravity"
    elif [ -d "$HOME/.config/opencode" ] || command -v opencode &> /dev/null; then
        echo "opencode"
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

# 플랫폼별 hooks/설정 설치
case "$PLATFORM" in
    claude)
        HOOKS_DIR="$HOME/.claude/hooks"
        mkdir -p "$HOOKS_DIR"
        echo -e "${YELLOW}► Claude Hooks 설치 중...${NC}"
        cp hooks/*.py "$HOOKS_DIR/" 2>/dev/null || true
        cp hooks/*.sh "$HOOKS_DIR/" 2>/dev/null || true
        chmod +x "$HOOKS_DIR"/*.sh 2>/dev/null || true
        ;;
    codex)
        CODEX_DIR="$HOME/.codex"
        mkdir -p "$CODEX_DIR"
        echo -e "${YELLOW}► Codex 설정 중...${NC}"
        if [ -f "$CODEX_DIR/config.toml" ]; then
            if ! grep -q "agents.sage-loop" "$CODEX_DIR/config.toml" 2>/dev/null; then
                echo "" >> "$CODEX_DIR/config.toml"
                cat hooks/codex/config.toml >> "$CODEX_DIR/config.toml"
            fi
        else
            cp hooks/codex/config.toml "$CODEX_DIR/config.toml"
        fi
        if [ -f "$CODEX_DIR/instructions.md" ]; then
            if ! grep -q "Sage Loop" "$CODEX_DIR/instructions.md" 2>/dev/null; then
                echo "" >> "$CODEX_DIR/instructions.md"
                cat hooks/codex/instructions.md >> "$CODEX_DIR/instructions.md"
            fi
        else
            cp hooks/codex/instructions.md "$CODEX_DIR/instructions.md"
        fi
        ;;
    antigravity)
        echo -e "${YELLOW}► Antigravity 스킬 설치 완료${NC}"
        # Skills already installed by apply_overlay.py
        ;;
    opencode)
        OPENCODE_DIR="$HOME/.config/opencode"
        mkdir -p "$OPENCODE_DIR"
        echo -e "${YELLOW}► OpenCode 에이전트 설치 완료${NC}"
        # Agents already installed by apply_overlay.py
        ;;
    cursor)
        echo -e "${YELLOW}► Cursor 룰 생성 완료${NC}"
        echo -e "  ${BLUE}프로젝트 루트에 .cursor/rules/ 확인${NC}"
        ;;
    vscode)
        echo -e "${YELLOW}► VS Code 설정 생성 완료${NC}"
        echo -e "  ${BLUE}프로젝트 루트에 .github/instructions/ 확인${NC}"
        ;;
esac

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✓ 설치 완료!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "사용법:"
case "$PLATFORM" in
    claude)
        echo -e "  ${BLUE}/sage \"작업 내용\"${NC}              # Sage Loop 시작"
        echo -e "  ${BLUE}/sage --chain quick \"버그 수정\"${NC}  # Quick 체인"
        ;;
    codex|opencode)
        echo -e "  ${BLUE}sage-orchestrator \"작업 내용\"${NC}"
        echo -e "  ${BLUE}sage-orchestrator --status${NC}"
        ;;
    antigravity)
        echo -e "  ${BLUE}/sage \"작업 내용\"${NC}              # Antigravity에서 실행"
        ;;
    cursor|vscode)
        echo -e "  ${BLUE}@sage-<role> 참조하여 역할 실행${NC}"
        echo -e "  ${BLUE}sage-orchestrator CLI 사용${NC}"
        ;;
esac
echo
echo -e "문서: https://github.com/seunghyuoffice-design/sage-loop"
