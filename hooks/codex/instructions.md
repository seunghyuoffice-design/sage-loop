# Sage Loop Instructions for Codex

## Slash Commands

When the user types `/sage <task>`, you must:

1. **Start the chain**: Run `sage-orchestrator "<task>"`
2. **Execute each role**: The CLI will tell you which role to execute next
3. **Report completion**: Run `sage-orchestrator --complete <role> --result "pass"`
4. **Continue until done**: Repeat until the chain completes

## Available Commands

```bash
# Start a new chain
sage-orchestrator "Implement feature X"

# Quick chain (faster, for simple tasks)
sage-orchestrator --chain quick "Fix bug Y"

# Check current status
sage-orchestrator --status

# Complete a role
sage-orchestrator --complete critic --result "pass"
sage-orchestrator --complete architect --result "pass"

# Reset session
sage-orchestrator --reset
```

## Chain Types

| Command | Chain | Use Case |
|---------|-------|----------|
| `/sage` | FULL | Complex features, major changes |
| `/sage --chain quick` | QUICK | Bug fixes, small changes |
| `/sage --chain review` | REVIEW | Code review only |
| `/sage --chain design` | DESIGN | Architecture planning |

## Role Execution

When executing a role, follow its specific instructions:

- **Sage**: Accept/authorize/approve (appears 3 times)
- **Ideator**: Generate 50+ ideas without judgment
- **Analyst**: Filter to top 5 ideas with reasoning
- **Critic**: Identify risks only, no solutions
- **Censor**: Block rule violations
- **Architect**: Design the implementation
- **Executor**: Implement the design exactly
- **Validator**: Quality gate pass/fail

## Example Flow

```
User: /sage "Add dark mode toggle"

You: Starting sage-loop chain...
> sage-orchestrator "Add dark mode toggle"
NEXT: sage

You: [Execute Sage role - accept petition]
> sage-orchestrator --complete sage --result "pass"
NEXT: ideator

You: [Execute Ideator - generate 50+ ideas]
> sage-orchestrator --complete ideator --result "pass"
NEXT: analyst

... continue until CHAIN_COMPLETE ...
```
