#!/usr/bin/env python3
"""List active claude-* tmux sessions in table, json, or names format."""

import os
import shutil
import subprocess
import sys


def tmux(*args):
    """Run a tmux command, returning (returncode, stdout)."""
    result = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


def has_sessions():
    rc, _ = tmux("list-sessions")
    return rc == 0


def get_role(session):
    rc, out = tmux("show-environment", "-t", session, "CLAUDE_AGENT_ROLE")
    role = ""
    if rc == 0:
        for line in out.splitlines():
            if line.startswith("CLAUDE_AGENT_ROLE="):
                role = line[len("CLAUDE_AGENT_ROLE="):]
                break

    if not role:
        if "orchestrator" in session:
            role = "orchestrator"
        elif "planner" in session:
            role = "planner"
        elif "builder" in session:
            role = "builder"
        elif "generator" in session:
            role = "generator"
        elif "reviewer" in session:
            role = "reviewer"
        elif "security" in session:
            role = "security-reviewer"
        elif "research" in session:
            role = "researcher"
        elif "tester" in session:
            role = "tester"
        else:
            role = "unknown"

    return role


def get_workdir(session):
    rc, out = tmux("display-message", "-p", "-t", session, "#{pane_pid}")
    pane_pid = out.strip() if rc == 0 else ""

    cwd = ""
    if pane_pid:
        cwd_path = f"/proc/{pane_pid}/cwd"
        try:
            cwd = os.readlink(cwd_path)
        except OSError:
            cwd = ""

    return cwd or "unknown"


def get_status(session):
    rc, out = tmux("display-message", "-p", "-t", session, "#{pane_dead}")
    dead = out.strip() if rc == 0 else "1"
    return "dead" if dead == "1" else "active"


def list_sessions(prefix):
    rc, out = tmux("list-sessions", "-F", "#{session_name}")
    if rc != 0:
        return []
    sessions = [s for s in out.splitlines() if s.startswith(prefix)]
    sessions.sort()
    return sessions


def main():
    prefix = os.environ.get("CLAUDE_AGENT_PREFIX", "claude-")
    fmt = sys.argv[1] if len(sys.argv) > 1 else "table"

    if shutil.which("tmux") is None:
        print("Missing tmux", file=sys.stderr)
        sys.exit(1)

    if not has_sessions():
        if fmt == "json":
            print("[]")
        elif fmt == "names":
            pass
        else:
            print("No active tmux sessions.")
        sys.exit(0)

    sessions = list_sessions(prefix)

    if fmt == "names":
        for session in sessions:
            print(session)

    elif fmt == "json":
        print("[")
        first = True
        for session in sessions:
            role = get_role(session)
            status = get_status(session)
            workdir = get_workdir(session)

            if not first:
                print(",")
            first = False

            print(
                f'  {{"session":"{session}","role":"{role}",'
                f'"status":"{status}","workdir":"{workdir}"}}',
                end="",
            )
        print()
        print("]")

    else:  # table (default)
        print(f"{'SESSION':<24} {'ROLE':<20} {'STATUS':<10} WORKDIR")
        print(f"{'-------':<24} {'----':<20} {'------':<10} -------")
        for session in sessions:
            role = get_role(session)
            status = get_status(session)
            workdir = get_workdir(session)
            print(f"{session:<24} {role:<20} {status:<10} {workdir}")


if __name__ == "__main__":
    main()
