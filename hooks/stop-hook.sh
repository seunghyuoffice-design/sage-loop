#!/bin/bash
# Sage Loop - Stop Hook (v2)
#
# sage 체인 실행 중 종료를 차단하고 다음 역할 실행 유도
# JSON 출력 + exit 0으로 Claude에게 명확한 신호 전달
#
# 핵심 변경 (v2):
#   - exit 1 → exit 0 + JSON (Claude가 신호를 받을 수 있도록)
#   - {"decision": "block", "reason": "..."} → 계속 실행
#   - exit 0 (JSON 없음) → 정상 종료
#
# 환경변수:
#   SAGE_STATE_DIR: 상태 파일 디렉토리 (기본: /tmp)
#   SAGE_PROJECT_ROOT: 프로젝트 루트 (기본: /home/rovers/Dyarchy-v3)
#   SAGE_MAX_LOOPS: 최대 루프 횟수 (기본: 50)
#   SAGE_SESSION_TIMEOUT: 세션 타임아웃 초 (기본: 3600)
#   SAGE_SESSION_ID: 세션 ID (없으면 자동 생성)
#   SAGE_DEBUG: 디버그 모드 (기본: 0)

set -e

# 환경변수 기반 설정
STATE_DIR="${SAGE_STATE_DIR:-/tmp}"
PROJECT_ROOT="${SAGE_PROJECT_ROOT:-/home/rovers/Dyarchy-v3}"
MAX_LOOPS="${SAGE_MAX_LOOPS:-50}"
SESSION_TIMEOUT="${SAGE_SESSION_TIMEOUT:-3600}"

# JSON 출력 함수
output_continue() {
  local reason="$1"
  local next_role="$2"
  local progress="$3"

  cat <<EOF
{"decision":"block","reason":"$reason","next_role":"$next_role","progress":"$progress","instruction":"다음 역할 '$next_role'를 즉시 실행하세요. /sage 체인 진행 중입니다."}
EOF
}

# 세션 ID 획득
if [[ -z "$SAGE_SESSION_ID" ]]; then
  SAGE_SESSION_ID=$(python3 -c "
import sys, time, hashlib
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from src.sage.session import get_session_id
    print(get_session_id())
except:
    print(hashlib.md5(str(time.time()).encode()).hexdigest()[:8])
" 2>/dev/null || echo "$(date +%s | md5sum | head -c 8)")
  export SAGE_SESSION_ID
fi

SESSION_FILE="${STATE_DIR}/sage_session_${SAGE_SESSION_ID}.json"
LOOP_FILE="${STATE_DIR}/sage_loop_state_${SAGE_SESSION_ID}.json"
ERROR_LOG="${STATE_DIR}/sage_errors_${SAGE_SESSION_ID}.log"

# 디버그 로그 함수
debug_log() {
  if [[ "${SAGE_DEBUG:-0}" == "1" ]]; then
    echo "[DEBUG] $(date +%H:%M:%S) $1" >> "$ERROR_LOG"
  fi
}

# 세션 cleanup 함수
cleanup_session() {
  rm -f "$SESSION_FILE" "$LOOP_FILE" 2>/dev/null || true
  rm -f "${STATE_DIR}/sage_circuit_breaker_${SAGE_SESSION_ID}.json" 2>/dev/null || true
  [[ "${SAGE_DEBUG:-0}" != "1" ]] && rm -f "$ERROR_LOG" 2>/dev/null || true
}

debug_log "Stop hook started. Session: $SAGE_SESSION_ID"

# ═══════════════════════════════════════════════════════════════
# 1. sage 세션 활성 여부 확인
# ═══════════════════════════════════════════════════════════════

if [[ ! -f "$SESSION_FILE" ]]; then
  debug_log "No session file. Normal exit."
  exit 0
fi

is_active=$(jq -r '.active // false' "$SESSION_FILE" 2>/dev/null || echo "false")
if [[ "$is_active" != "true" ]]; then
  debug_log "Session not active. Normal exit."
  exit 0
fi

# ═══════════════════════════════════════════════════════════════
# 2. 루프 카운터 및 타임아웃 확인
# ═══════════════════════════════════════════════════════════════

if [[ -f "$LOOP_FILE" ]]; then
  loop_count=$(jq -r '.loop_count // 0' "$LOOP_FILE" 2>/dev/null || echo 0)
  started_at=$(jq -r '.started_at // ""' "$LOOP_FILE" 2>/dev/null || echo "")
else
  loop_count=0
  started_at=""
fi

# 하드 리미트 체크
if [[ $loop_count -ge $MAX_LOOPS ]]; then
  debug_log "MAX_LOOPS ($MAX_LOOPS) reached. Allowing exit."
  cleanup_session
  exit 0
fi

# 타임아웃 체크
if [[ -n "$started_at" ]]; then
  current_time=$(date +%s)
  start_time=$(python3 -c "
from datetime import datetime
try:
    dt = datetime.fromisoformat('$started_at'.replace('Z', '+00:00'))
    print(int(dt.timestamp()))
except:
    print($current_time)
" 2>/dev/null || echo $current_time)
  elapsed=$((current_time - start_time))

  if [[ $elapsed -ge $SESSION_TIMEOUT ]]; then
    debug_log "Timeout (${SESSION_TIMEOUT}s). Allowing exit."
    cleanup_session
    exit 0
  fi
fi

# ═══════════════════════════════════════════════════════════════
# 3. 완료 신호 확인
# ═══════════════════════════════════════════════════════════════

exit_signal=$(jq -r '.exit_signal // false' "$SESSION_FILE" 2>/dev/null || echo "false")
pending_feedback=$(python3 "$PROJECT_ROOT/.claude/hooks/feedback_checker.py" 2>>"$ERROR_LOG" || echo "0")

if [[ "$exit_signal" == "true" ]] && [[ "$pending_feedback" == "0" ]]; then
  exit_reason=$(jq -r '.exit_reason // "체인 완료"' "$SESSION_FILE" 2>/dev/null || echo "체인 완료")
  debug_log "EXIT_SIGNAL: true. Reason: $exit_reason"
  cleanup_session
  exit 0
fi

# ═══════════════════════════════════════════════════════════════
# 4. Circuit breaker 체크
# ═══════════════════════════════════════════════════════════════

if ! python3 "$PROJECT_ROOT/.claude/hooks/circuit_breaker_check.py" 2>>"$ERROR_LOG"; then
  debug_log "Circuit breaker open. Allowing exit."
  cleanup_session
  exit 0
fi

# ═══════════════════════════════════════════════════════════════
# 5. 현재 역할 자동 완료 처리 (v3)
# ═══════════════════════════════════════════════════════════════

current_role=$(jq -r '.current_role // ""' "$SESSION_FILE" 2>/dev/null || echo "")
completed_list=$(jq -r '.completed_roles[]? // empty' "$SESSION_FILE" 2>/dev/null || echo "")

# 현재 역할이 있고 아직 완료되지 않았으면 자동 완료 처리
if [[ -n "$current_role" ]] && ! echo "$completed_list" | grep -q "^${current_role}#"; then
  debug_log "Auto-completing role: $current_role"
  python3 -m sage_loop.cli.orchestrator --complete "$current_role" --result "auto-complete by stop-hook" 2>>"$ERROR_LOG" || true
fi

# ═══════════════════════════════════════════════════════════════
# 6. 다음 역할 확인 및 Claude에게 신호 전달
# ═══════════════════════════════════════════════════════════════

# 세션 정보 재로드 (완료 처리 후)
next_role=$(python3 "$PROJECT_ROOT/.claude/hooks/role_detector.py" --next 2>/dev/null || echo "")
current_role=$(jq -r '.current_role // ""' "$SESSION_FILE" 2>/dev/null || echo "")
chain_type=$(jq -r '.chain_type // "FULL"' "$SESSION_FILE" 2>/dev/null || echo "FULL")
task=$(jq -r '.task // ""' "$SESSION_FILE" 2>/dev/null || echo "")

# 진행 상황 계산
total_roles=$(jq -r '.chain_roles | length' "$SESSION_FILE" 2>/dev/null || echo "0")
completed_roles=$(jq -r '.completed_roles | length' "$SESSION_FILE" 2>/dev/null || echo "0")
progress="${completed_roles}/${total_roles}"

# 루프 카운터 증가
new_count=$((loop_count + 1))
if [[ -z "$started_at" ]]; then
  started_at=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)
fi

echo "{\"loop_count\": $new_count, \"started_at\": \"$started_at\", \"session_id\": \"$SAGE_SESSION_ID\"}" > "$LOOP_FILE"

debug_log "Loop $new_count: current=$current_role, next=$next_role, progress=$progress"

# ═══════════════════════════════════════════════════════════════
# 6. JSON 출력 (Claude에게 신호 전달)
# ═══════════════════════════════════════════════════════════════

if [[ -n "$next_role" ]]; then
  # 다음 역할이 있으면 계속 진행 신호
  reason="[SAGE $chain_type] Loop $new_count/$MAX_LOOPS: '$current_role' → '$next_role' ($progress)"
  output_continue "$reason" "$next_role" "$progress"
else
  # 다음 역할이 없으면 완료 처리
  python3 "$PROJECT_ROOT/.claude/hooks/sage_state_manager.py" exit --reason "모든 역할 완료" 2>/dev/null || true
  cleanup_session
fi

# exit 0 필수: JSON이 Claude에게 전달되려면 exit 0이어야 함
exit 0
