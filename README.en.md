# Sage Loop

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/seunghyuoffice-design/sage-loop/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-blueviolet.svg)](https://claude.ai/claude-code)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg)]()

English | **[한국어](README.md)**

**14-phase autonomous agent orchestration system** — Inspired by Korea's Joseon Dynasty governance (1392-1897)

> *"What if your AI agent worked like a 500-year-old government bureaucracy?"*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SAGE LOOP v1.3                                   │
│                                                                             │
│   "Review it"           "Execute it"          "Confirm completion"          │
│       ↓                     ↓                       ↓                       │
│   ┌──────┐              ┌──────┐               ┌──────┐                     │
│   │ SAGE │ ────────────→│ SAGE │ ─────────────→│ SAGE │                     │
│   │  #1  │              │  #2  │               │  #3  │                     │
│   └──────┘              └──────┘               └──────┘                     │
│       │                     ↑                      ↑                        │
│       ▼                     │                      │                        │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │              14-Phase Deliberation Chain                          │     │
│   └───────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why Sage Loop?

Most AI agent frameworks are either:
- **Too simple**: Single-pass execution with no checks
- **Too chaotic**: Multiple agents with no structure

Sage Loop provides **structured deliberation** — the same process that governed Korea for 500 years:

| Problem | Sage Loop Solution |
|---------|-------------------|
| AI makes unchecked decisions | **Three Offices** review every plan |
| No separation of concerns | **Six Ministries** handle specialized domains |
| Single point of failure | **Chief Councilor** appears 3 times for oversight |
| No quality enforcement | **Dokseol** (harsh feedback) forces rigor |

## Quick Start

```bash
# One-line install
curl -fsSL https://raw.githubusercontent.com/seunghyuoffice-design/sage-loop/main/install.sh | bash

# Run
/sage "Implement user authentication system"
```

---

## The 14-Phase Flow

```
SAGE #1 "Review it"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2-4: 6 Ministries (Ideator → Analyst → Formatter) x6     │
│  Personnel | Finance | Rites | Military | Justice | Works       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Phase 5: Chief Secretary merges all
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 6: Three Offices parallel review                         │
│  Censor (criticism) | Inspector (rules) | Scholars (academia)   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Phase 7: Architect designs  →  Phase 8: Left/Right Councilors review
    │
    ▼
SAGE #2 "Execute it"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 10-11: 6 Executors (parallel) → Chief Secretary merges   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Phase 12: Secret Inspector + Quality Checker
    │
    ▼
SAGE #3 "Confirm completion"
    │
    ▼
Phase 14: Logger | Reviewer | Improver (record/reflect/enhance)
```

---

## Core Concepts

### The Six Ministries (6조)

Each request is processed by **6 specialized departments in parallel**:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        Six Ministries (Yukjo)                              │
├───────────┬───────────┬───────────┬───────────┬───────────┬───────────────┤
│   Ijo     │   Hojo    │   Yejo    │ Byeongjo  │ Hyeongjo  │    Gongjo     │
│ Personnel │  Finance  │   Rites   │  Military │  Justice  │    Works      │
├───────────┼───────────┼───────────┼───────────┼───────────┼───────────────┤
│ Roles &   │ Resources │ Documents │ Security  │ Rules &   │ Infra &       │
│ Skills    │ & Budget  │ & Protocol│ & Ops     │ Compliance│ Build         │
├───────────┴───────────┴───────────┴───────────┴───────────┴───────────────┤
│                                                                           │
│  Phase 2: Ideators  → Generate ideas (haiku model)                       │
│  Phase 3: Analysts  → Filter & analyze (haiku model)                     │
│  Phase 4: Formatters → Format for submission (haiku model)               │
│                                                                           │
│  ※ All 6 ministries run in PARALLEL                                      │
└───────────────────────────────────────────────────────────────────────────┘
```

### The Three Offices (삼사)

**Independent review bodies** that check every plan:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Three Offices (Samsa)                             │
├─────────────────────┬─────────────────────┬─────────────────────────────┤
│     Sagawon         │     Saheonbu        │       Hongmungwan           │
│ Office of Censor    │ Office of Inspector │    Office of Scholars       │
├─────────────────────┼─────────────────────┼─────────────────────────────┤
│ Criticize plans     │ Enforce rules       │ Provide references          │
│ Point out risks     │ Block violations    │ Academic guidance           │
├─────────────────────┼─────────────────────┼─────────────────────────────┤
│ Output: Risk list   │ Output: PASS/BLOCK  │ Output: Academic opinion    │
├─────────────────────┴─────────────────────┴─────────────────────────────┤
│                                                                         │
│ Dokseol (Harsh Feedback):                                               │
│ • "This isn't criticism, it's flattery" (Sagawon)                       │
│ • "I see you're trying to bypass the rules" (Saheonbu)                  │
│ • "Claims without evidence aren't scholarship" (Hongmungwan)            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### The Chief State Councilor (Sage)

Appears **3 times** throughout the process:

| Appearance | Phase | Role | Output |
|------------|-------|------|--------|
| 1st | Phase 1 | Receive petition | "Review it" |
| 2nd | Phase 9 | Approve execution | "Execute it" |
| 3rd | Phase 13 | Final confirmation | "Confirm completion" |

This mirrors the historical role of the 영의정 (Chief State Councilor), who oversaw all government decisions.

---

## Chain Types

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FULL (14 Phases) - Complete deliberation                                │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ Sage → [6 Ideators] → [6 Analysts] → [6 Formatters] → Merge             │
│     → [3 Offices] → Architect → [Left ∥ Right Councilor] → Sage         │
│     → [6 Executors] → Merge → [Inspector ∥ QA] → Sage                   │
│     → [Logger ∥ Reviewer ∥ Improver]                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ QUICK (5 Phases) - Fast execution                                       │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                         │
│ Censor → Architect → Executor → [Inspector ∥ QA] → Logger               │
├─────────────────────────────────────────────────────────────────────────┤
│ REVIEW (2 Phases) - Review only                                         │
│ ━━━━━━━━━━━━━━━━━━                                                      │
│ [Censor ∥ QA]                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ DESIGN (4 Phases) - Design only                                         │
│ ━━━━━━━━━━━━━━━━━━━━━━━━                                                │
│ Ideator → Analyst → Censor → Architect                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Installation

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/seunghyuoffice-design/sage-loop/main/install.sh | bash
```

### Supported Platforms

| Platform | Command |
|----------|---------|
| Claude Code | `curl ... \| bash -s claude` |
| OpenAI Codex | `curl ... \| bash -s codex` |
| Antigravity | `curl ... \| bash -s antigravity` |
| OpenCode | `curl ... \| bash -s opencode` |
| Cursor | `curl ... \| bash -s cursor` |
| VS Code | `curl ... \| bash -s vscode` |

### Manual Install

```bash
git clone https://github.com/seunghyuoffice-design/sage-loop.git
cd sage-loop
make install        # Claude Code (default)
# make install-codex  # OpenAI Codex
```

---

## Usage

### With Claude Code

```bash
# Basic execution
/sage "Implement user authentication"

# Specify chain type
/sage --chain quick "Fix login bug"
/sage --chain design "Design API architecture"
/sage --chain research "Research performance optimization"
```

### CLI

```bash
# Start new chain
python orchestrator.py "Implement feature X"

# Complete a role
python orchestrator.py --complete critic --result "pass"

# Check status
python orchestrator.py --status

# Reset
python orchestrator.py --reset
```

### Example Session

```
$ /sage "Implement API authentication"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 1: Sage (Chief State Councilor)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Review it. Petition for API authentication system received."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 2: Six Ministry Ideators (parallel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Personnel] JWT vs Session authentication proposal
[Finance] Token storage cost analysis
[Rites] API documentation format proposal
[Military] Security policy draft
[Justice] OWASP compliance checklist
[Works] Redis session store infrastructure proposal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 6: Three Offices (parallel review)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Censor] ⚠️ JWT expiration handling logic missing
[Inspector] ✓ PASS - No license violations
[Scholars] 📚 RFC 7519 JWT standard referenced

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 13: Sage (Chief State Councilor) - Final Approval
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Confirm completion. API authentication system approved."

EXIT_SIGNAL: APPROVED
```

---

## Model Configuration

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Model Configuration                             │
├────────────────────┬─────────────────────┬───────────────────────────────┤
│ Role Type          │ Claude Code         │ OpenAI Codex                  │
├────────────────────┼─────────────────────┼───────────────────────────────┤
│ Supervision        │ opus + ultrathink   │ gpt-5.2 + reasoning:high      │
│ (sage, 3 offices)  │                     │                               │
├────────────────────┼─────────────────────┼───────────────────────────────┤
│ Implementation     │ sonnet              │ gpt-5.2-codex                 │
│ (executor, arch)   │                     │                               │
├────────────────────┼─────────────────────┼───────────────────────────────┤
│ Generation         │ haiku               │ gpt-5.1-codex-mini            │
│ (ideator, analyst) │                     │                               │
└────────────────────┴─────────────────────┴───────────────────────────────┘
```

---

## Architecture

```
sage-loop/
├── skills/                    # Role definitions (platform-agnostic)
│   ├── yeong-ui-jeong/        # Orchestrator (Chief Councilor)
│   │   ├── SKILL.md           # L2 skill definition
│   │   ├── reference.md       # Detailed guide
│   │   └── scripts/           # L3 helper scripts
│   ├── sagawon.md             # Office of Censor
│   ├── saheonbu.md            # Office of Inspector
│   ├── hongmungwan.md         # Office of Scholars
│   └── ...
├── overlays/                  # Platform-specific configurations
│   ├── claude/
│   ├── codex/
│   ├── antigravity/
│   ├── cursor/
│   ├── opencode/
│   └── vscode/
├── hooks/                     # Claude Code hooks
├── src/sage_loop/
│   ├── engine/                # Core orchestration
│   ├── cli/                   # CLI tools
│   └── schemas.py             # Data models
└── pyproject.toml
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Parallel Execution** | 6 ministries process simultaneously (Phases 2-4, 10) |
| **Independent Review** | 3 offices review in parallel (Phase 6) |
| **Dokseol** | Harsh quality enforcement messages per role |
| **3× Sage Oversight** | Chief appears 3 times (receive/approve/confirm) |
| **6 Platforms** | Claude, Codex, Antigravity, Cursor, OpenCode, VSCode |
| **Overlay System** | Platform-specific model/config separation |
| **Thread-safe** | fcntl.flock + atomic writes |
| **Circuit Breaker** | Built-in loop prevention |

---

## Historical Background

Sage Loop is inspired by the **Uijeongbu (의정부)** system of Korea's Joseon Dynasty (1392-1897):

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Joseon Government Structure                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                         ┌─────────────┐                                 │
│                         │ Yeonguijeong│ ← Chief State Councilor         │
│                         │ (영의정)    │                                 │
│                         └──────┬──────┘                                 │
│                    ┌───────────┼───────────┐                            │
│                    ▼                       ▼                            │
│              ┌───────────┐           ┌───────────┐                      │
│              │Jwauijeong │           │ Uuijeong  │                      │
│              │ (좌의정)  │           │ (우의정)  │                      │
│              │   Left    │           │   Right   │                      │
│              └───────────┘           └───────────┘                      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Six Ministries (육조)                         │   │
│  ├────────┬────────┬────────┬────────┬────────┬─────────────────────┤   │
│  │  Ijo   │  Hojo  │  Yejo  │Byeongjo│Hyeongjo│  Gongjo             │   │
│  │Personnel│Finance│ Rites │Military│Justice │  Works              │   │
│  └────────┴────────┴────────┴────────┴────────┴─────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Three Offices (삼사)                          │   │
│  ├────────────────────┬────────────────────┬────────────────────────┤   │
│  │      Sagawon       │      Saheonbu      │      Hongmungwan       │   │
│  │  (Remonstrance)    │    (Inspection)    │     (Scholarship)      │   │
│  └────────────────────┴────────────────────┴────────────────────────┘   │
│                                                                         │
│  This system provided checks and balances for 500 years.                │
│  Sage Loop adapts these principles for AI agent orchestration.         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## License

MIT License

---

<p align="center">
  <i>"What works for 500 years might work for AI too."</i>
</p>
