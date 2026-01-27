# sage-loop Makefile
# 간편 설치/관리

.PHONY: install install-claude install-codex uninstall clean help

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
	@pip install -e . -q 2>/dev/null || true
	@echo "✓ Done! Use: sage-orchestrator \"your task\""

# 제거
uninstall:
	@echo "Uninstalling sage-loop..."
	@rm -rf ~/.claude/skills/sage ~/.claude/skills/yeong-ui-jeong 2>/dev/null || true
	@rm -rf ~/.claude/skills/ideator ~/.claude/skills/critic 2>/dev/null || true
	@rm -f ~/.claude/hooks/sage_*.py ~/.claude/hooks/stop-hook.sh 2>/dev/null || true
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
	@echo "Usage:"
	@echo "  make install        # Claude Code 설치 (기본)"
	@echo "  make install-claude # Claude Code 설치"
	@echo "  make install-codex  # OpenAI Codex 설치"
	@echo "  make uninstall      # 제거"
	@echo "  make clean          # 캐시 정리"
