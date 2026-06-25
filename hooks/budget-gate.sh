#!/usr/bin/env bash
# T Harness — token budget gate (Claude Code PreToolUse hook).
#
# This runs synchronously before every matched tool call, so it must be
# near-instant. It reads ONLY two small files written by budget-sampler.py:
#   - $DIR/paused     sentinel; present iff usage is over budget (holds reason)
#   - $DIR/heartbeat  touched on every sampler run; used for staleness checks
#
# It never calls ccusage or parses large JSON. The expensive sampling is done
# out-of-band by budget-sampler.py (kicked here in the background, or by a
# `claude_budget.py watch` loop / cron).
#
# Contract (PreToolUse):
#   exit 0, no output  -> allow (normal permission flow proceeds)
#   exit 2 + stderr    -> deny the tool call; stderr is shown to Claude
#
# Intentionally no `set -e`: a benign non-zero from a probe must not abort.

DIR="${CLAUDE_TOKEN_GATE_DIR:-$HOME/.claude/token-gate}"
PAUSED="$DIR/paused"
HEARTBEAT="$DIR/heartbeat"
STALE_AFTER="${CLAUDE_TOKEN_GATE_STALE_AFTER:-180}"
FAIL_CLOSED="${CLAUDE_TOKEN_GATE_FAIL_CLOSED:-0}"
AUTO_REFRESH="${CLAUDE_TOKEN_GATE_AUTO_REFRESH:-1}"
INTERVAL="${CLAUDE_TOKEN_GATE_INTERVAL:-30}"

# Drain hook stdin without spawning a subprocess (avoids broken-pipe).
IFS= read -r -d '' _ <&0 2>/dev/null || true

now=$(printf '%(%s)T' -1 2>/dev/null || echo 0)

heartbeat_age() {
  # Echoes seconds since last heartbeat, or -1 if missing/unknown.
  local hb
  hb=$(stat -c %Y "$HEARTBEAT" 2>/dev/null) || { echo -1; return; }
  echo $(( now - hb ))
}

# Opportunistic background refresh: keeps state fresh with no daemon required.
# Fire-and-forget — never adds latency to this tool call.
if [[ "$AUTO_REFRESH" == "1" ]]; then
  age=$(heartbeat_age)
  if [[ "$age" -lt 0 || "$age" -ge "$INTERVAL" ]]; then
    sampler="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/budget-sampler.py"
    if [[ -f "$sampler" ]]; then
      setsid python3 "$sampler" >/dev/null 2>&1 </dev/null &
      disown 2>/dev/null || true
    fi
  fi
fi

# Hard stop: the sampler decided usage is over budget.
if [[ -f "$PAUSED" ]]; then
  reason=$(<"$PAUSED")
  [[ -z "$reason" ]] && reason="Paused by token budget gate."
  printf '%s\n' "$reason" >&2
  exit 2
fi

# Fail-closed (opt-in): refuse when no fresh usage data is available.
if [[ "$FAIL_CLOSED" == "1" ]]; then
  age=$(heartbeat_age)
  if [[ "$age" -lt 0 ]]; then
    echo "Token gate: no sampler heartbeat yet (fail-closed)." >&2
    exit 2
  fi
  if [[ "$age" -ge "$STALE_AFTER" ]]; then
    echo "Token gate: sampler state is stale (${age}s old, fail-closed)." >&2
    exit 2
  fi
fi

exit 0
