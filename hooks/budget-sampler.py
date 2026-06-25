#!/usr/bin/env python3
"""T Harness — token budget sampler.

Samples Claude Code session usage (via get-usage.py, which calls `claude -p
/usage`) and maintains the state that the PreToolUse gate (budget-gate.sh)
reads. This is the EXPENSIVE half of the budget system and must never run on
the tool-call hot path. It is invoked by:
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

SCRIPT_DIR = Path(__file__).resolve().parent
GET_USAGE = SCRIPT_DIR / "get-usage.py"


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
        "pause_threshold": _resolve(cfg, "pause_threshold", "CLAUDE_PAUSE_THRESHOLD", 0.50, float),
    }


def read_usage():
    """Current session usage as a decimal fraction (e.g. 0.51 = 51% used).

    Returns a float on success, or None if usage cannot be determined.
    None means "cannot enforce".
    """
    try:
        raw = subprocess.check_output(
            ["python3", str(GET_USAGE)],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        return float(raw.strip())
    except Exception:
        return None


def load_state():
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"paused": False}


def atomic_write(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def run_once(now):
    DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    usage = read_usage()
    state = load_state()

    enforce = usage is not None
    snoozed = now < float(state.get("snooze_until", 0))
    paused = False
    reason = ""

    if enforce and not snoozed:
        if usage >= cfg["pause_threshold"]:
            paused = True
            reason = (
                f"Session usage is at {usage * 100:.1f}%, at or above the "
                f"{int(cfg['pause_threshold'] * 100)}% pause threshold."
            )

    # A manual pause set via `claude_budget.py pause` overrides sampling.
    if state.get("manual_pause"):
        paused = True
        reason = state.get("reason") or "Manually paused by operator."

    state.update({
        "updated_at": now,
        "usage": usage,
        "pause_threshold": cfg["pause_threshold"],
        "enforced": enforce,
        "snoozed": snoozed,
        "paused": paused,
        "reason": reason,
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
