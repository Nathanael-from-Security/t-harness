#!/usr/bin/env python3
"""T Harness — token budget sampler.

Samples Claude Code token usage (via `ccusage`) and maintains the state that the
PreToolUse gate (budget-gate.sh) reads. This is the EXPENSIVE half of the budget
system and must never run on the tool-call hot path. It is invoked by:
  - the gate's opportunistic background refresh (no daemon required), or
  - `claude_budget.py watch` (a polling loop), or
  - cron / systemd timer.

State directory (default ~/.claude/token-gate), overridable via
CLAUDE_TOKEN_GATE_DIR:
  state.json   rich state for the CLI and the sampler's own history
  config.json  persisted limits/thresholds (written by `claude_budget.py set`)
  paused       sentinel read by the gate; present iff over budget (holds reason)
  heartbeat    touched every run; the gate uses its mtime for staleness
  sampler.lock flock target preventing concurrent samplers
"""

import fcntl
import json
import os
import subprocess
import time
from pathlib import Path

DIR = Path(os.environ.get(
    "CLAUDE_TOKEN_GATE_DIR",
    str(Path.home() / ".claude" / "token-gate"),
))
STATE_PATH = DIR / "state.json"
CONFIG_PATH = DIR / "config.json"
PAUSED_PATH = DIR / "paused"
HEARTBEAT_PATH = DIR / "heartbeat"
LOCK_PATH = DIR / "sampler.lock"

# Minimum prior usage before the growth-spike rule applies, to avoid noisy
# ratios when the 5-hour window has only just started.
GROWTH_MIN_BASELINE = 10_000


def _resolve(cfg, key, env, default, cast):
    """Env var wins, then persisted config.json, then the built-in default."""
    if env in os.environ:
        return cast(os.environ[env])
    if key in cfg:
        return cast(cfg[key])
    return default


def load_config():
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except Exception:
        cfg = {}
    return {
        "token_limit": _resolve(cfg, "token_limit", "CLAUDE_5H_TOKEN_LIMIT", 500_000, int),
        "five_hour_threshold": _resolve(cfg, "five_hour_threshold", "CLAUDE_5H_THRESHOLD", 0.80, float),
        "growth_threshold": _resolve(cfg, "growth_threshold", "CLAUDE_1M_GROWTH_THRESHOLD", 1.10, float),
        "lookback_seconds": _resolve(cfg, "lookback_seconds", "CLAUDE_TOKEN_GATE_LOOKBACK_SECONDS", 60, int),
    }


def read_tokens():
    """Total tokens in the active 5-hour usage block.

    Counts only fresh tokens (input + output + cacheCreationInputTokens),
    excluding cache-read tokens, to match Anthropic's 5-hour rate limit
    enforcement which excludes cached tokens from the limit.

    Returns an int on success, or None if usage cannot be determined (ccusage
    missing, errored, or unparseable). None means "cannot enforce".
    """
    ccusage = os.environ.get("CCUSAGE_BIN", "ccusage")
    try:
        raw = subprocess.check_output(
            [ccusage, "blocks", "--json", "--active", "--offline"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
    except Exception:
        return None

    try:
        data = json.loads(raw)
    except Exception:
        return None

    active = [b for b in (data.get("blocks") or []) if b.get("isActive")]
    if not active:
        return 0

    counts = active[0].get("tokenCounts") or {}
    return sum(
        int(counts.get(k, 0) or 0)
        for k in ("inputTokens", "outputTokens", "cacheCreationInputTokens")
    )


def load_state():
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"samples": [], "paused": False}


def atomic_write(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def previous_sample(samples, now, lookback):
    """Most recent sample at least `lookback` seconds before now."""
    older = [s for s in samples if s.get("ts", 0) <= now - lookback]
    return max(older, key=lambda s: s["ts"]) if older else None


def run_once(now):
    DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    current = read_tokens()
    state = load_state()
    samples = state.get("samples", [])

    enforce = current is not None
    snoozed = now < float(state.get("snooze_until", 0))
    paused = False
    reason = ""

    if enforce and not snoozed:
        hard_limit = int(cfg["token_limit"] * cfg["five_hour_threshold"])
        if current >= hard_limit:
            paused = True
            reason = (
                f"Active 5-hour usage is {current:,} tokens, at or above "
                f"{int(cfg['five_hour_threshold'] * 100)}% of the configured "
                f"{cfg['token_limit']:,}-token limit."
            )
        else:
            prev = previous_sample(samples, now, cfg["lookback_seconds"])
            if prev and int(prev.get("tokens", 0)) > GROWTH_MIN_BASELINE:
                ratio = current / int(prev["tokens"])
                if ratio >= cfg["growth_threshold"]:
                    paused = True
                    reason = (
                        f"Token usage rose from {int(prev['tokens']):,} to "
                        f"{current:,} in about {cfg['lookback_seconds']}s "
                        f"({ratio:.2f}x)."
                    )

    if current is not None:
        samples.append({"ts": now, "tokens": current})

    # A manual pause set via `claude_budget.py pause` overrides sampling.
    if state.get("manual_pause"):
        paused = True
        reason = state.get("reason") or "Manually paused by operator."

    state.update({
        "updated_at": now,
        "current_tokens": current,
        "token_limit": cfg["token_limit"],
        "five_hour_threshold": cfg["five_hour_threshold"],
        "enforced": enforce,
        "snoozed": snoozed,
        "paused": paused,
        "reason": reason,
        "samples": samples[-30:],
    })
    atomic_write(STATE_PATH, json.dumps(state, indent=2))

    # Sentinel is the gate's fast read path.
    if paused:
        atomic_write(PAUSED_PATH, reason or "Paused by token budget gate.")
    else:
        try:
            PAUSED_PATH.unlink()
        except FileNotFoundError:
            pass

    HEARTBEAT_PATH.touch()
    return state


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return  # another sampler holds the lock; skip this run
    try:
        run_once(time.time())
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    main()
