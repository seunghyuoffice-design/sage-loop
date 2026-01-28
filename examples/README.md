# Sage Loop Examples

Real-world usage examples for Sage Loop.

## Quick Examples

### 1. Feature Implementation

```bash
/sage "Implement user authentication with JWT"
```

**What happens:**
- 6 ministries generate ideas in parallel
- 3 offices review for risks, compliance, and best practices
- Architect creates implementation plan
- 6 executors implement in parallel
- Inspectors verify the result

### 2. Bug Fix (Quick Chain)

```bash
/sage --chain quick "Fix null pointer exception in login handler"
```

**What happens:**
- Censor reviews the fix plan
- Architect designs minimal fix
- Executor implements
- Inspectors verify

### 3. Code Review (Review Chain)

```bash
/sage --chain review "Review PR #123"
```

**What happens:**
- Censor identifies issues
- QA checker validates

### 4. Architecture Design (Design Chain)

```bash
/sage --chain design "Design microservices architecture for payment system"
```

**What happens:**
- Ideator brainstorms approaches
- Analyst evaluates trade-offs
- Censor identifies risks
- Architect creates design document

---

## Detailed Walkthrough

### Example: Implementing a REST API

**Input:**
```bash
/sage "Implement REST API for user management with CRUD operations"
```

**Phase 1 - Sage receives:**
```
영의정: "검토하라. 사용자 관리 REST API 구현 청원을 접수하였다."
(Review it. Petition for user management REST API received.)
```

**Phase 2 - Six Ideators produce:**
```
[이조/Personnel] Role-based access control design
[호조/Finance] Database connection pooling for cost efficiency
[예조/Rites] OpenAPI 3.0 documentation format
[병조/Military] Rate limiting and security headers
[형조/Justice] GDPR compliance for user data
[공조/Works] Docker deployment configuration
```

**Phase 6 - Three Offices review:**
```
[사간원/Censor] ⚠️ Missing input validation on email field
[사헌부/Inspector] ✓ PASS - MIT licensed dependencies only
[홍문관/Scholars] 📚 Recommend: REST API Design Rulebook (O'Reilly)
```

**Phase 9 - Sage approves:**
```
영의정: "시행하라. 지적 사항 반영 후 구현을 허가한다."
(Execute it. Implementation approved after addressing concerns.)
```

**Phase 10 - Six Executors implement:**
```
[이조] Created: src/auth/roles.py
[호조] Created: src/db/pool.py
[예조] Created: docs/openapi.yaml
[병조] Created: src/middleware/security.py
[형조] Created: src/handlers/privacy.py
[공조] Created: Dockerfile, docker-compose.yml
```

**Phase 13 - Sage confirms:**
```
영의정: "완료 확인. 사용자 관리 API 구현을 승인한다."
(Confirm completion. User management API implementation approved.)

EXIT_SIGNAL: APPROVED
```

---

## Chain Selection Guide

| Scenario | Recommended Chain | Reason |
|----------|------------------|--------|
| New feature | `FULL` | Maximum review and quality |
| Bug fix | `QUICK` | Fast with essential checks |
| PR review | `REVIEW` | Focused on criticism |
| System design | `DESIGN` | Focus on architecture |
| Research | `RESEARCH` | Academic depth |

---

## Custom Role Usage

### Invoke specific role:

```bash
# Run only the censor
/sagawon "Review this authentication implementation"

# Run only the architect
/dohwaseo "Design the database schema"

# Run only the inspector
/saheonbu "Check RULES compliance"
```

---

## Programmatic Usage

```python
from sage_loop import SageLoop

# Initialize
sage = SageLoop()

# Start full chain
result = sage.run(
    agenda="Implement caching layer",
    chain="FULL"
)

# Check result
if result.exit_signal == "APPROVED":
    print("Implementation complete!")
else:
    print(f"Blocked: {result.block_reason}")
```

---

## Tips

1. **Be specific** - "Implement JWT auth with refresh tokens" > "Add auth"
2. **Use appropriate chain** - Don't use FULL for simple fixes
3. **Trust the process** - Let all phases complete for best results
4. **Read Dokseol** - Harsh feedback reveals real issues
