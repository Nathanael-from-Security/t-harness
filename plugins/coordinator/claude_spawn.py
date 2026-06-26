#!/usr/bin/env python3
"""Spawn (or attach to) a Claude Code agent running inside a tmux session."""

import argparse
import os
import shutil
import subprocess
import sys
import time


def tmux(*args, **kwargs):
    return subprocess.run(["tmux", *args], **kwargs)


def has_session(session):
    return tmux("has-session", "-t", session, capture_output=True).returncode == 0


def install_tmux_keybinds():
    # Ctrl-b S: interactive session picker.
    tmux("bind-key", "S", "choose-tree", "-s")

    # Ctrl-b A: prompt for a tmux session name and switch to it.
    tmux(
        "bind-key", "A",
        "command-prompt", "-p", "Switch to session:",
        "switch-client -t '%%'",
    )

    # Ctrl-b n: switch to next claude-* session.
    tmux("bind-key", "n", "run-shell", r'''
    current="$(tmux display-message -p "#{session_name}")"
    sessions="$(tmux list-sessions -F "#{session_name}" | grep "^claude-" | sort || true)"

    if [ -z "$sessions" ]; then
      tmux display-message "No claude-* sessions found"
      exit 0
    fi

    next="$(printf "%s\n" "$sessions" | awk -v cur="$current" "found {print; exit} \$0 == cur {found=1}")"

    if [ -z "$next" ]; then
      next="$(printf "%s\n" "$sessions" | head -n 1)"
    fi

    tmux switch-client -t "$next"
  ''')

    # Ctrl-b p: switch to previous claude-* session.
    tmux("bind-key", "p", "run-shell", r'''
    current="$(tmux display-message -p "#{session_name}")"
    sessions="$(tmux list-sessions -F "#{session_name}" | grep "^claude-" | sort || true)"

    if [ -z "$sessions" ]; then
      tmux display-message "No claude-* sessions found"
      exit 0
    fi

    prev="$(printf "%s\n" "$sessions" | awk -v cur="$current" "\$0 == cur {print last; exit} {last=\$0}")"

    if [ -z "$prev" ]; then
      prev="$(printf "%s\n" "$sessions" | tail -n 1)"
    fi

    tmux switch-client -t "$prev"
  ''')


def main():
    parser = argparse.ArgumentParser(
        description="Spawn (or attach to) a Claude Code agent running inside a tmux session."
    )
    parser.add_argument(
        "--name",
        default="orchestrator",
        metavar="AGENT_NAME",
        help="Role/name for the agent (e.g. builder, reviewer). Default: orchestrator",
    )
    parser.add_argument(
        "--dir",
        default=None,
        metavar="WORKDIR",
        help="Working directory for the agent. Default: current directory",
    )
    parser.add_argument(
        "--session",
        default=None,
        metavar="SESSION_NAME",
        help="Tmux session name. Default: claude-<name>",
    )
    args = parser.parse_args()

    agent_name = args.name
    workdir = args.dir if args.dir is not None else os.getcwd()
    session_name = args.session if args.session is not None else f"claude-{agent_name}"
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    agents_bin = os.environ.get("AGENTS_BIN", os.path.join(script_dir, "claude_agents.py"))
    send_bin = os.environ.get("SEND_BIN", os.path.join(script_dir, "claude_talk.py"))

    if shutil.which("tmux") is None:
        print("Missing tmux", file=sys.stderr)
        sys.exit(1)

    if shutil.which(claude_bin) is None:
        print(f"Missing Claude executable: {claude_bin}", file=sys.stderr)
        sys.exit(1)

    if not (os.path.isfile(agents_bin) and os.access(agents_bin, os.X_OK)):
        print(f"Missing or non-executable agent list helper: {agents_bin}", file=sys.stderr)
        sys.exit(1)

    if not (os.path.isfile(send_bin) and os.access(send_bin, os.X_OK)):
        print(f"Missing or non-executable send helper: {send_bin}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(workdir):
        print(f"Working directory does not exist: {workdir}", file=sys.stderr)
        sys.exit(1)

    # Install/update tmux keybinds even if the session already exists.
    install_tmux_keybinds()

    if has_session(session_name):
        if os.environ.get("TMUX"):
            os.execvp("tmux", ["tmux", "switch-client", "-t", session_name])
        else:
            os.execvp("tmux", ["tmux", "attach-session", "-t", session_name])

    tmux("new-session", "-d", "-s", session_name, "-c", workdir)

    tmux("set-environment", "-t", session_name, "CLAUDE_AGENT_NAME", agent_name)
    tmux("set-environment", "-t", session_name, "CLAUDE_AGENT_SESSION", session_name)
    tmux("set-environment", "-t", session_name, "CLAUDE_AGENT_WORKDIR", workdir)

    tmux("rename-window", "-t", f"{session_name}:0", agent_name)

    tmux(
        "send-keys", "-t", session_name,
        f"export CLAUDE_AGENT_NAME='{agent_name}'; "
        f"export CLAUDE_AGENT_SESSION='{session_name}'; "
        f"export CLAUDE_AGENT_WORKDIR='{workdir}'; "
        f"exec {claude_bin}",
        "C-m",
    )

    time.sleep(2)

    intro = f"""You are running as a Claude Code agent inside tmux.

Dynamic agent context:

- Agent name: {agent_name}
- Tmux session: {session_name}
- Working directory: {workdir}

You are part of a multi-agent Claude system. Use /coordinator:manage-session to interact with other agents.

Do not send secrets, credentials, API keys, tokens, private data, or sensitive project material to another agent.

Do not modify Tmux sessions or environment variables of other agents.
"""

    subprocess.run([send_bin, session_name], input=intro, text=True)
    tmux("send-keys", "-t", session_name, "C-m", check=True)

    if os.environ.get("TMUX"):
        os.execvp("tmux", ["tmux", "switch-client", "-t", session_name])
    else:
        os.execvp("tmux", ["tmux", "attach-session", "-t", session_name])


if __name__ == "__main__":
    main()
