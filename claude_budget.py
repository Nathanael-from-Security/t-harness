#!/usr/bin/env python3
"""T Harness — token budget control CLI.

Front end for the budget gate/sampler pair:
  hooks/budget-gate.sh     PreToolUse hook; blocks tool calls when over budget
  hooks/budget-sampler.py  samples usage (ccusage) and writes the gate's state

Commands:
  status            show current usage, limit, and pause state
  set               persist limits/thresholds to config.json
  pause             manually pause (gate blocks tools until `resume`)
  resume            clear a pause and snooze auto-pause for a cooldown window
  sample            run one sampling pass now
  watch             poll: sample on an interval (daemon alternative)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DIR = Path(os.environ.get(
    "CLAUDE_TOKEN_GATE_DIR",
    str(Path.home() / ".claude" / "token-gate"),
))
STATE_PATH = DIR / "state.json"
CONFIG_PATH = DIR / "config.json"
PAUSED_PATH = DIR / "paused"

SAMPLER = Path(__file__).resolve().parent / "hooks" / "budget-sampler.py"

DEFAULT_SNOOZE = 1800  # seconds auto-pause stays suppressed after `resume`


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def atomic_write(path, text):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_state(state):
    atomic_write(STATE_PATH, json.dumps(state, indent=2))


def run_sampler():
    return subprocess.call([sys.executable, str(SAMPLER)])


# ----------------------------------------------------------------------------- commands


def cmd_status(args):
    state = load_json(STATE_PATH, {})
    if args.format == "json":
        print(json.dumps(state, indent=2))
        return

    if not state:
        print("No budget state yet. Run: claude_budget.py sample")
        return

    usage = state.get("usage")
    threshold = state.get("pause_threshold", 0)
    updated = state.get("updated_at", 0)
    age = int(time.time() - updated) if updated else None

    if usage is None:
        usage_str = "unknown (get-usage.py unavailable)"
    else:
        usage_str = f"{usage * 100:.1f}% of session limit"

    paused = state.get("paused")
    print(f"Usage:     {usage_str}")
    if threshold:
        print(f"Pause at:  {int(threshold * 100)}%")
    print(f"Enforced:  {'yes' if state.get('enforced') else 'no (no usage data)'}")
    print(f"Paused:    {'YES' if paused else 'no'}")
    if paused:
        print(f"Reason:    {state.get('reason', '')}")
    if state.get("snoozed"):
        remaining = int(float(state.get("snooze_until", 0)) - time.time())
        print(f"Snoozed:   auto-pause suppressed for ~{max(0, remaining)}s")
    if age is not None:
        print(f"Updated:   {age}s ago")


def cmd_set(args):
    cfg = load_json(CONFIG_PATH, {})
    if args.threshold is not None:
        cfg["pause_threshold"] = args.threshold
    atomic_write(CONFIG_PATH, json.dumps(cfg, indent=2))
    print("Config saved:")
    print(json.dumps(cfg, indent=2))


def cmd_pause(args):
    state = load_json(STATE_PATH, {"samples": []})
    reason = args.reason or "Manually paused by operator."
    state["manual_pause"] = True
    state["paused"] = True
    state["reason"] = reason
    state["snooze_until"] = 0
    write_state(state)
    atomic_write(PAUSED_PATH, reason)
    print(f"Paused. Tool calls will be blocked: {reason}")


def cmd_resume(args):
    state = load_json(STATE_PATH, {"samples": []})
    state["manual_pause"] = False
    state["paused"] = False
    state["reason"] = ""
    state["snooze_until"] = time.time() + args.snooze
    write_state(state)
    try:
        PAUSED_PATH.unlink()
    except FileNotFoundError:
        pass
    print(f"Resumed. Auto-pause suppressed for {args.snooze}s.")


def cmd_sample(args):
    if not SAMPLER.exists():
        print(f"Sampler not found: {SAMPLER}", file=sys.stderr)
        sys.exit(1)
    rc = run_sampler()
    if rc == 0:
        cmd_status(argparse.Namespace(format="table"))
    sys.exit(rc)


def cmd_watch(args):
    if not SAMPLER.exists():
        print(f"Sampler not found: {SAMPLER}", file=sys.stderr)
        sys.exit(1)
    print(f"Watching: sampling every {args.interval}s. Ctrl-C to stop.")
    try:
        while True:
            run_sampler()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(
        prog="claude_budget.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="show usage and pause state")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("set", help="persist pause threshold")
    p.add_argument("--threshold", type=float, help="session usage fraction to pause at (e.g. 0.50)")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("pause", help="manually pause (block tool calls)")
    p.add_argument("--reason", help="reason shown to the agent")
    p.set_defaults(func=cmd_pause)

    p = sub.add_parser("resume", help="clear pause and snooze auto-pause")
    p.add_argument("--snooze", type=int, default=DEFAULT_SNOOZE,
                   help=f"seconds to suppress auto-pause (default {DEFAULT_SNOOZE})")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("sample", help="run one sampling pass now")
    p.set_defaults(func=cmd_sample)

    p = sub.add_parser("watch", help="poll: sample on an interval")
    p.add_argument("--interval", type=int, default=30, help="seconds between samples")
    p.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
