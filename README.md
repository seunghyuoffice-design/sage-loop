# Sage Loop

A **14-phase autonomous agent orchestration system** with **6조 병렬 실행**, inspired by the Korean Joseon Dynasty's Uijeongbu (의정부) deliberation system.

## Overview

Sage Loop implements a hierarchical decision-making chain modeled after the Joseon Dynasty's Six Ministries (육조) system, enabling thorough analysis, critique, and execution of complex tasks.

**v5 Features:**
- 🏛️ **6조 체계**: 이조/호조/예조/병조/형조/공조 병렬 처리
- 🔀 **Parallel Execution**: 6개 역할 동시 실행
- 🗣️ **Dokseol Enforcement**: 역할별 품질 강제 메시지
- 🔒 **File Locking**: Thread-safe state management
- 🌐 **6 Platform Support**: Claude, Codex, Antigravity, Cursor, OpenCode, VSCode

The Sage (영의정) appears **three times**, following the historical Uijeongbu deliberation flow:

1. **Phase 1**: Accept petition ("검토하라")
2. **Phase 9**: Authorize execution ("시행하라")
3. **Phase 13**: Final approval ("완료 확인")

```text
Sage(접수) → [6조 낭청] → [6조 판서] → [6조 승지] → 도승지
    → [삼사 병렬] → 도화서 → [좌의정 ∥ 우의정] → Sage(허가)
    → [6조 집행관] → 도승지 → [암행어사 ∥ 교서관]
    → Sage(결재) → [춘추관 ∥ 승문원 ∥ 규장각]
```

## Roles (14 Phases)

| Phase | Role | Korean | Function | Type |
| ----- | ---- | ------ | -------- | ---- |
| 1 | **Sage** | 영의정 | **Accept petition** - "검토하라" | Sequential |
| 2 | ideator-* (x6) | 6조 낭청 | Generate ideas per ministry | **Parallel** |
| 3 | analyst-* (x6) | 6조 판서 | Analyze and filter ideas | **Parallel** |
| 4 | seungji-* (x6) | 6조 승지 | Format for deliberation | **Parallel** |
| 5 | doseungji | 도승지 | Consolidate and distribute to 삼사 | Sequential |
| 6 | sagawon + saheonbu + hongmungwan | 삼사 | Remonstrance + Compliance + Counsel | **Parallel** |
| 7 | dohwaseo | 도화서 | Design implementation | Sequential |
| 8 | jwauijeong + uuijeong | 좌의정 + 우의정 | Policy + Technical review | **Parallel** |
| 9 | **Sage** | 영의정 | **Authorize execution** - "시행하라" | Sequential |
| 10 | executor-* (x6) | 6조 집행관 | Execute per ministry | **Parallel** |
| 11 | doseungji | 도승지 | Consolidate execution results | Sequential |
| 12 | amhaeng + gyoseogwan | 암행어사 + 교서관 | Inspection + Validation | **Parallel** |
| 13 | **Sage** | 영의정 | **Final approval** - "완료 확인" | Sequential |
| 14 | chunchugwan + seungmunwon + gyujanggak | 춘추관 + 승문원 + 규장각 | Record + Reflect + Improve | **Parallel** |

### 6조 (Six Ministries)

| 조 | Korean | Domain |
| -- | ------ | ------ |
| 이조 (ijo) | 吏曹 | Personnel, roles |
| 호조 (hojo) | 戶曹 | Finance, resources |
| 예조 (yejo) | 禮曹 | Rites, documentation |
| 병조 (byeongjo) | 兵曹 | Operations, security |
| 형조 (hyeongjo) | 刑曹 | Justice, compliance |
| 공조 (gongjo) | 工曹 | Works, infrastructure |

## Chain Types

- **FULL**: All 14 phases with 6조 + 삼사 parallel execution (complex tasks)
- **QUICK**: 사간원 → 도화서 → Executor → [암행어사 ∥ 교서관] → 춘추관
- **REVIEW**: [사간원 ∥ 교서관]
- **DESIGN**: Ideator → Analyst → 사간원 → 도화서
- **RESEARCH**: [Ideator ∥ 홍문관] → Analyst → 사간원

## Installation

### 원클릭 설치 (One-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/seunghyuoffice-design/sage-loop/main/install.sh | bash
```

**6 Platforms Supported:**

```bash
curl ... | bash -s claude       # Claude Code (default)
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
├── claude/       # Claude Code
├── codex/        # OpenAI Codex
├── antigravity/  # Google Antigravity
├── cursor/       # Cursor IDE
├── opencode/     # OpenCode
└── vscode/       # VS Code Copilot
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

- **6조 Parallel Execution**: Six ministries run concurrently (v5)
- **Dokseol Enforcement**: Quality enforcement messages per role
- **Concurrency Safe**: File locking with `fcntl.flock` + atomic writes
- **6 Platform Support**: Claude, Codex, Antigravity, Cursor, OpenCode, VSCode
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

**의정부 (State Council):**
- **영의정 (Sage)**: Chief State Councilor - final authority
- **좌의정 (jwauijeong)**: Left State Councilor - internal affairs
- **우의정 (uuijeong)**: Right State Councilor - external affairs

**삼사 (Three Offices):**
- **사간원 (sagawon)**: Office of Remonstrance - critique and advice
- **사헌부 (saheonbu)**: Office of Inspector General - rule enforcement
- **홍문관 (hongmungwan)**: Office of Special Advisors - academic counsel

**육조 (Six Ministries):**
- **이조**: Personnel | **호조**: Finance | **예조**: Rites
- **병조**: Military | **형조**: Justice | **공조**: Works

**기타 (Others):**
- **승정원 (도승지)**: Royal Secretariat - coordination
- **규장각**: Royal Library - knowledge archive
- **춘추관**: Office of Annals - historical record

## License

MIT License

## Contributing

Contributions welcome! Please read our contributing guidelines.
