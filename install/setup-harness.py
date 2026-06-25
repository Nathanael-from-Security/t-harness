#!/usr/bin/env python3
"""T Harness installer.

Wires the token budget gate into Claude Code:
  1. Verifies `ccusage` is installed (the sampler needs it to read usage).
  2. Merges the PreToolUse budget-gate hook into settings.json without
     clobbering existing settings or duplicating the hook.

Usage:
  install/setup-harness.py [--settings PATH] [--matcher REGEX] [--timeout N]

Defaults to the user settings file at ~/.claude/settings.json.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Repo root is the parent of this install/ directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "hooks" / "budget-gate.sh"

DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"
DEFAULT_MATCHER = "Read|Bash|Write|Edit|MultiEdit|Task|WebFetch|WebSearch"
DEFAULT_TIMEOUT = 5


def check_ccusage():
    if shutil.which(os.environ.get("CCUSAGE_BIN", "ccusage")) is None:
        print(
            "ERROR: ccusage is not installed or not on PATH.\n"
            "The budget sampler reads token usage via ccusage; without it the\n"
            "gate cannot enforce limits.\n\n"
            "Install it, for example:\n"
            "  npm install -g ccusage\n",
            file=sys.stderr,
        )
        sys.exit(1)


def load_settings(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)


def merge_hook(settings, command, matcher, timeout):
    """Insert the gate into hooks.PreToolUse, returning True if changed."""
    hooks = settings.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])

    hook_entry = {"type": "command", "command": command, "timeout": timeout}

    # Reuse a matcher block if one already exists; otherwise add a new one.
    for block in pre:
        if block.get("matcher") == matcher:
            block_hooks = block.setdefault("hooks", [])
            if any(h.get("command") == command for h in block_hooks):
                return False  # already installed
            block_hooks.append(hook_entry)
            return True

    pre.append({"matcher": matcher, "hooks": [hook_entry]})
    return True


def write_settings(path, settings):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2) + "\n")
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS,
                        help=f"settings.json to modify (default {DEFAULT_SETTINGS})")
    parser.add_argument("--matcher", default=DEFAULT_MATCHER,
                        help="PreToolUse matcher regex")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="hook timeout in seconds")
    args = parser.parse_args()

    if not GATE.exists():
        print(f"ERROR: gate script not found: {GATE}", file=sys.stderr)
        sys.exit(1)

    check_ccusage()
    print("ccusage: found")

    settings = load_settings(args.settings)
    changed = merge_hook(settings, str(GATE), args.matcher, args.timeout)

    if not changed:
        print(f"Hook already present in {args.settings}; nothing to do.")
        return

    write_settings(args.settings, settings)
    print(f"Installed PreToolUse budget gate into {args.settings}")
    print(f"  matcher: {args.matcher}")
    print(f"  command: {GATE}")
    print(f"  timeout: {args.timeout}s")


if __name__ == "__main__":
    main()
