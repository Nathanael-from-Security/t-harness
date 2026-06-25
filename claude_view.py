#!/usr/bin/env python3
"""Attach to (or switch the current client to) a Claude agent tmux session."""

import os
import shutil
import subprocess
import sys


def tmux(*args, **kwargs):
    return subprocess.run(["tmux", *args], **kwargs)


def main():
    session_name = sys.argv[1] if len(sys.argv) > 1 else ""

    if not session_name:
        print(f"Usage: {sys.argv[0]} <session-name>", file=sys.stderr)
        print(file=sys.stderr)
        print("Active sessions:", file=sys.stderr)
        tmux("list-sessions", "-F", "  #{session_name}")
        sys.exit(1)

    if shutil.which("tmux") is None:
        print("Missing tmux", file=sys.stderr)
        sys.exit(1)

    if tmux("has-session", "-t", session_name, capture_output=True).returncode != 0:
        print(f"No such tmux session: {session_name}", file=sys.stderr)
        sys.exit(1)

    if os.environ.get("TMUX"):
        os.execvp("tmux", ["tmux", "switch-client", "-t", session_name])
    else:
        os.execvp("tmux", ["tmux", "attach-session", "-t", session_name])


if __name__ == "__main__":
    main()
