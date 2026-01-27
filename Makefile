# sage-loop Makefile
# 간편 설치/관리 - 6개 플랫폼 지원

.PHONY: install install-claude install-codex install-antigravity install-opencode install-cursor install-vscode uninstall clean help

# 기본: Claude Code 설치
install: install-claude

# Claude Code 설치
install-claude:
	@echo "Installing for Claude Code..."
	@python3 scripts/apply_overlay.py claude
	@mkdir -p ~/.claude/hooks
	@cp -f hooks/*.py ~/.claude/hooks/ 2>/dev/null || true
	@cp -f hooks/*.sh ~/.claude/hooks/ 2>/dev/null || true
	@chmod +x ~/.claude/hooks/*.sh 2>/dev/null || true
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Use: /sage \"your task\""

# Codex 설치
install-codex:
	@echo "Installing for Codex..."
	@python3 scripts/apply_overlay.py codex
	@mkdir -p ~/.codex
	@test -f ~/.codex/config.toml && cat hooks/codex/config.toml >> ~/.codex/config.toml || cp hooks/codex/config.toml ~/.codex/
	@test -f ~/.codex/instructions.md && cat hooks/codex/instructions.md >> ~/.codex/instructions.md || cp hooks/codex/instructions.md ~/.codex/
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Use: sage-orchestrator \"your task\""

# Antigravity 설치
install-antigravity:
	@echo "Installing for Antigravity..."
	@python3 scripts/apply_overlay.py antigravity
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Use: /sage \"your task\""

# OpenCode 설치
install-opencode:
	@echo "Installing for OpenCode..."
	@python3 scripts/apply_overlay.py opencode
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Agents installed to ~/.config/opencode/agents/"

# Cursor 설치
install-cursor:
	@echo "Installing for Cursor..."
	@python3 scripts/apply_overlay.py cursor
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Rules installed to .cursor/rules/"

# VS Code 설치
install-vscode:
	@echo "Installing for VS Code Copilot..."
	@python3 scripts/apply_overlay.py vscode
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Instructions installed to .github/instructions/"

# 제거
uninstall:
	@echo "Uninstalling sage-loop..."
	@rm -rf ~/.claude/skills/sage ~/.claude/skills/yeong-ui-jeong 2>/dev/null || true
	@rm -rf ~/.claude/skills/ideator ~/.claude/skills/critic 2>/dev/null || true
	@rm -f ~/.claude/hooks/sage_*.py ~/.claude/hooks/stop-hook.sh 2>/dev/null || true
	@rm -rf ~/.gemini/antigravity/skills/sage 2>/dev/null || true
	@rm -rf ~/.config/opencode/agents/sage*.md 2>/dev/null || true
	@rm -rf .cursor/rules/sage-*.mdc 2>/dev/null || true
	@rm -rf .github/instructions/sage-*.instructions.md 2>/dev/null || true
	@pip uninstall sage-loop -y 2>/dev/null || true
	@echo "✓ Uninstalled"

# 캐시 정리
clean:
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned"

# 도움말
help:
	@echo "sage-loop Makefile"
	@echo ""
	@echo "Platforms:"
	@echo "  make install            # Claude Code (default)"
	@echo "  make install-claude     # Claude Code"
	@echo "  make install-codex      # OpenAI Codex"
	@echo "  make install-antigravity # Google Antigravity"
	@echo "  make install-opencode   # OpenCode"
	@echo "  make install-cursor     # Cursor IDE"
	@echo "  make install-vscode     # VS Code Copilot"
	@echo ""
	@echo "Other:"
	@echo "  make uninstall          # Remove all"
	@echo "  make clean              # Clear cache"
