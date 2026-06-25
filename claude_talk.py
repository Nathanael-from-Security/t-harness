#!/usr/bin/env python3
"""Send a message to a Claude agent running in a tmux session."""

import shutil
import subprocess
import sys
import time


def tmux(*args, **kwargs):
    return subprocess.run(["tmux", *args], **kwargs)


def has_session(session):
    return tmux(
        "has-session", "-t", session,
        capture_output=True,
    ).returncode == 0


def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("Usage: claude-send <session-name> <message...>", file=sys.stderr)
        print("   or: echo 'message' | claude-send <session-name>", file=sys.stderr)
        sys.exit(1)

    session_name = sys.argv[1]
    rest = sys.argv[2:]

    if shutil.which("tmux") is None:
        print("Missing tmux", file=sys.stderr)
        sys.exit(1)

    if not has_session(session_name):
        print(f"No such tmux session: {session_name}", file=sys.stderr)
        sys.exit(1)

    if rest:
        message = " ".join(rest)
    else:
        message = sys.stdin.read()

    if not message:
        print("No message provided", file=sys.stderr)
        sys.exit(1)

    # Load message into tmux buffer, paste it into the session, then press Enter.
    tmux("load-buffer", "-", input=message, text=True)
    tmux("paste-buffer", "-p", "-t", session_name)
    time.sleep(0.1)
    tmux("send-keys", "-t", session_name, "Enter")


if __name__ == "__main__":
    main()
