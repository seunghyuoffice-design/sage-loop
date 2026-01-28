#!/bin/bash
# sage-reinstall.sh - Auto reinstall sage-loop after git push
# Used as a PostToolUse hook in Claude Code

set -euo pipefail

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only trigger on Bash tool with git push
[[ "$TOOL" != "Bash" ]] && exit 0
[[ ! "$COMMAND" =~ git\ push ]] && exit 0

# Only in sage-loop directory
CWD=$(pwd)
[[ ! "$CWD" =~ sage-loop ]] && exit 0

# Background reinstall
pip install --force-reinstall --break-system-packages \
    git+https://github.com/seunghyuoffice-design/sage-loop.git \
    >/dev/null 2>&1 &

echo "sage-loop reinstall triggered (background)"
