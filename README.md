# Sage Loop

A 14-phase autonomous agent orchestration system with **parallel execution support**, inspired by the Korean Joseon Dynasty's Uijeongbu (의정부) deliberation system.

## Overview

Sage Loop implements a hierarchical decision-making chain where each role has specific responsibilities, enabling thorough analysis, critique, and execution of complex tasks.

**v4 Features:**
- 🔀 **Parallel Execution**: Non-blocking roles run concurrently
- 🔒 **File Locking**: Thread-safe state management with `fcntl.flock`
- ⚡ **Atomic Writes**: Corruption-proof state persistence

The Sage (영의정) appears **three times**, following the historical Uijeongbu deliberation flow:

1. **Phase 1**: Accept petition and initiate review ("검토하라")
2. **Phase 9**: Authorize execution after deliberation ("시행하라")
3. **Phase 12**: Final approval after validation ("완료 확인")

```text
Sage(접수) → Ideator → Analyst → Critic → Censor → Academy → Architect
    → [LeftState ∥ RightState] → Sage(허가) → Executor
    → [Inspector ∥ Validator] → Sage(결재) → Historian → [Reflector ∥ Improver]
```

## Roles (14 Phases, 17 Roles)

| Phase | Role | Korean | Function | Type |
| ----- | ---- | ------ | -------- | ---- |
| 1 | **Sage** | 영의정 | **Accept petition (1st)** - "검토하라" | Sequential |
| 2 | Ideator | 현인 | Generate 50+ ideas | Sequential |
| 3 | Analyst | 선지자 | Filter to 5 best ideas | Sequential |
| 4 | Critic | 비조 | Identify risks (no solutions) | Sequential |
| 5 | Censor | 파수꾼 | Block rule violations | Sequential |
| 6 | Academy | 대제학 | Provide academic guidance | Sequential |
| 7 | Architect | 장인 | Design implementation | Sequential |
| 8 | LeftState + RightState | 좌의정 + 우의정 | Policy + Technical review | **Parallel** |
| 9 | **Sage** | 영의정 | **Execution authorization (2nd)** - "시행하라" | Sequential |
| 10 | Executor | 실행관 | Implement the design | Sequential |
| 11 | Inspector + Validator | 감찰관 + 검증관 | Inspect + Quality gate | **Parallel** |
| 12 | **Sage** | 영의정 | **Final approval (3rd)** - "완료 확인" | Sequential |
| 13 | Historian | 역사관 | Record decisions | Sequential |
| 14 | Reflector + Improver | 회고관 + 개선관 | Feedback + Improvements | **Parallel** |

## Chain Types

- **FULL**: All 14 phases with 3 parallel groups (complex tasks)
- **QUICK**: Critic → Architect → Executor → [Inspector ∥ Validator] → Historian
- **REVIEW**: Critic → Validator
- **DESIGN**: Ideator → Analyst → Critic → Architect
- **RESEARCH**: Ideator → Analyst → Academy → Historian

## Installation

### 원클릭 설치 (One-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/seunghyuoffice-design/sage-loop/main/install.sh | bash
```

다른 플랫폼:

```bash
curl ... | bash -s codex        # OpenAI Codex
curl ... | bash -s antigravity  # Google Antigravity
curl ... | bash -s opencode     # OpenCode
curl ... | bash -s cursor       # Cursor IDE
curl ... | bash -s vscode       # VS Code Copilot
```

### Git Clone 설치

```bash
git clone https://github.com/seunghyuoffice-design/sage-loop.git
cd sage-loop
make install        # Claude Code (기본)
# make install-codex  # OpenAI Codex
```

### 수동 설치

```bash
git clone https://github.com/seunghyuoffice-design/sage-loop.git
cd sage-loop

# 오버레이 적용
python3 scripts/apply_overlay.py claude   # For Claude Code
python3 scripts/apply_overlay.py codex    # For OpenAI Codex

# Hooks 복사 (Claude Code only)
cp hooks/* ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
```

### Manual Installation (Claude Code)

```bash
# Copy skills to your Claude Code project
cp -r skills/* ~/.claude/skills/

# Copy hooks
cp hooks/* ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
```

### As Python Package

```bash
pip install -e .
```

## Cross-Platform Support

sage-loop is platform-agnostic at its core. Skills are defined without model specifications, allowing you to run them on any LLM platform.

### Overlay System

Platform-specific configurations are managed through **overlays**:

```text
overlays/
├── claude/
│   └── model_map.yaml   # Claude models + ultrathink
└── codex/
    └── model_map.yaml   # Codex models + reasoning_effort
```

### Model Mapping

| Role Type | Claude | Codex |
| --------- | ------ | ----- |
| Supervision (sage, critic, censor) | opus + ultrathink | gpt-5.2 + reasoning:high |
| Implementation (executor, architect) | sonnet | gpt-5.2-codex |
| Generation (ideator, analyst) | haiku | gpt-5.1-codex-mini |

### Custom Overlays

Create your own overlay for other platforms:

```yaml
# overlays/my-platform/model_map.yaml
platform: my-platform
skills_path: ~/.my-platform/skills/

models:
  sage: { model: my-best-model, thinking: extended }
  ideator: { model: my-fast-model }
```

## Usage

### With Claude Code

```bash
# Invoke Sage Loop
/sage "Implement user authentication"

# Use specific chain
/sage --chain quick "Fix the login bug"
```

### CLI (Orchestrator v4)

```bash
# Start a new chain
python orchestrator.py "Implement feature X"

# Complete a role
python orchestrator.py --complete critic --result "pass"

# Complete parallel roles (both at once or separately)
python orchestrator.py --complete left-state-councilor --result "pass"
python orchestrator.py --complete right-state-councilor --result "pass"

# Check status
python orchestrator.py --status

# Reset session
python orchestrator.py --reset
```

**Parallel Execution Output:**
```
NEXT_PARALLEL: left-state-councilor, right-state-councilor
# After completing one:
PARALLEL_PROGRESS: left-state-councilor 완료
PENDING: right-state-councilor
# After completing both:
NEXT: sage
```

### Programmatic Usage

```python
from sage_loop.engine.sage_commander import SageCommander
from sage_loop.schemas import ChainType

commander = SageCommander()
result = await commander.execute_chain(
    session_id="my-session",
    user_request="Implement feature X",
    chain_type=ChainType.FULL
)
```

## Architecture

```text
sage-loop/
├── skills/           # Role definitions (platform-agnostic)
│   ├── yeong-ui-jeong/  # Orchestrator skill (영의정)
│   ├── ideator.md
│   ├── critic.md
│   └── ...
├── overlays/         # Platform-specific configurations
│   ├── claude/       # Claude Code overlay
│   └── codex/        # OpenAI Codex overlay
├── scripts/
│   └── apply_overlay.py
├── hooks/            # Claude Code hooks
├── src/sage_loop/
│   ├── engine/       # Core orchestration
│   ├── cli/          # CLI tools
│   ├── hooks/        # Phase hooks
│   └── schemas.py    # Data models
└── pyproject.toml
```

## Key Features

- **Parallel Execution**: Non-blocking roles run concurrently (v4)
- **Concurrency Safe**: File locking with `fcntl.flock` + atomic writes (v4)
- **Platform Agnostic**: Core skills work on any LLM platform
- **Overlay System**: Platform-specific model/thinking configuration
- **Context Isolation**: Each role runs in isolated context via Task tool
- **Branching**: Dynamic branching based on role outputs
- **Circuit Breaker**: Prevents infinite loops
- **Feedback Loop**: Roles can request re-evaluation
- **State Persistence**: File-based with atomic updates

## Environment Variables

```bash
SAGE_REDIS_HOST=localhost
SAGE_REDIS_PORT=6380
SAGE_MAX_LOOPS=50
SAGE_SESSION_TIMEOUT=3600
SAGE_DEBUG=0
```

## Auto-Approval Settings

Sage Loop runs multiple commands during chain execution. To prevent approval prompts from interrupting the flow, configure auto-approval for each platform.

### Claude Code (~/.claude/settings.json)

```json
{
  "permissions": {
    "allow": [
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(git:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(mv:*)",
      "Bash(docker:*)",
      "Bash(.venv/bin/*:*)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

### OpenAI Codex (~/.codex/config.toml)

```toml
model = "gpt-5.2-codex"
approval_policy = "on-failure"
sandbox_mode = "workspace-write"

[projects."/your/project/path"]
trust_level = "trusted"
```

**approval_policy options:**
- `untrusted`: Only safe read commands auto-run (default)
- `on-failure`: Auto-run in sandbox, prompt on failure (recommended)
- `on-request`: Model decides when to ask
- `never`: Never prompt (risky)

Reference: [Codex Config Reference](https://developers.openai.com/codex/config-reference/)

## Historical Inspiration

The system draws from Korea's Joseon Dynasty (1392-1897) governance:

- **영의정 (Sage)**: Chief State Councilor - final authority
- **좌의정 (LeftState)**: Left State Councilor - internal affairs
- **우의정 (RightState)**: Right State Councilor - external/practical affairs
- **육조 (Six Ministries)**: Specialized departments under the councilors

## License

MIT License

## Contributing

Contributions welcome! Please read our contributing guidelines.
