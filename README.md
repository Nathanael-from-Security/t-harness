# T Harness

Multi-agent orchestration toolkit for running Claude Code agents in parallel tmux sessions.

## Quick Start

```bash
# Start a builder agent
./claude_spawn.py claude-builder builder ~/src/project

# List all active claude-* agents
./claude_agents.py

# Send a message to an agent
./claude_talk.py claude-builder "your message here"

# View/attach to an agent's session
./claude_view.py claude-builder
```

## Scripts

### `claude_agents.py`

List all active `claude-*` tmux sessions.

**Usage:**
```bash
./claude_agents.py [format]
```

**Formats:**
- `table` (default) — formatted columns (SESSION, ROLE, STATUS, WORKDIR)
- `json` — JSON array of session objects
- `names` — one session name per line

**Output example (table):**
```
SESSION                  ROLE                 STATUS     WORKDIR
-------                  ----                 ------     -------
claude-builder           builder              active     /home/user/src/project
claude-security          security-reviewer    active     /home/user/src/project
```

**Output example (json):**
```json
[
  {"session":"claude-builder","role":"builder","status":"active","workdir":"/home/user/src/project"},
  {"session":"claude-security","role":"security-reviewer","status":"active","workdir":"/home/user/src/project"}
]
```

**Environment variables:**
- `CLAUDE_AGENT_PREFIX` (default: `claude-`) — prefix to filter sessions

---

### `claude_talk.py`

Send a message to a Claude agent's tmux session.

**Usage:**
```bash
./claude_talk.py <session-name> [message...]
echo 'message' | ./claude_talk.py <session-name>
```

**Examples:**
```bash
# Send a single-line message
./claude_talk.py claude-builder "Check for lint errors"

# Send a multiline message
cat <<'MSG' | ./claude_talk.py claude-builder
Review the auth flow for:
- session handling
- token validation
MSG
```

The message is loaded into tmux's paste buffer and sent to the session as if you typed it.

---

### `claude_view.py`

Attach to (or switch the client to) a Claude agent's tmux session.

**Usage:**
```bash
./claude_view.py <session-name>
```

**Examples:**
```bash
# Attach to the builder session
./claude_view.py claude-builder

# If inside another tmux session, switch to the builder
./claude_view.py claude-builder
```

If no session name is provided, lists all active sessions.

---

### `claude_spawn.py`

Spawn a new Claude Code agent inside a tmux session, or attach to an existing one.

**Usage:**
```bash
./claude_spawn.py <session-name> <agent-name> [workdir]
```

**Examples:**
```bash
# Start a builder agent
./claude_spawn.py claude-builder builder ~/src/project

# Start a security reviewer
./claude_spawn.py claude-security security-reviewer ~/src/project

# Start a researcher with default cwd
./claude_spawn.py claude-research researcher
```

**Behavior:**
- If the session already exists, attaches to it (switches client if inside tmux, else attaches)
- If new, creates a tmux session, sets agent environment variables, starts `claude` CLI in the window
- Installs tmux keybindings for session navigation (Ctrl-b n/p for next/previous, Ctrl-b S for picker, Ctrl-b A for session switcher)
- Sends an introductory message showing the agent its name, session, and available coordination tools

**Environment variables:**
- `CLAUDE_BIN` (default: `claude`) — path to Claude CLI executable
- `AGENTS_BIN` (default: `<script-dir>/claude_agents.py`) — path to agents list script
- `SEND_BIN` (default: `<script-dir>/claude_talk.py`) — path to talk script

**Agent roles** (inferred from session name if not set via `CLAUDE_AGENT_ROLE` env var):
- `planner` — planning/design
- `builder` — implementation
- `reviewer` — code review
- `security-reviewer` — security review
- `researcher` — research/investigation
- `unknown` — default fallback

---

## Coordination Patterns

### Basic workflow

1. Spawn agents:
   ```bash
   ./claude_spawn.py claude-builder builder ~/src/project
   ```

2. In one agent, ask another agent for help:
   ```bash
   ./claude_talk.py claude-security "Review this auth PR for vulns"
   ```

3. Check on all agents:
   ```bash
   ./claude_agents.py
   ```

4. View a specific agent:
   ```bash
   ./claude_view.py claude-security
   ```

### Multiline messages

```bash
cat <<'MSG' | ./claude_talk.py claude-reviewer
I've finished the refactor. Please review:
- Performance impact on login flow
- Backwards compatibility with existing sessions
MSG
```

### Integration with shell scripts

```bash
#!/bin/bash
agents=$(./claude_agents.py names)
for agent in $agents; do
  ./claude_talk.py "$agent" "Check for test coverage gaps"
done
```

---

## Requirements

- `tmux` — session management
- Python 3.6+ — script runtime
- `claude` CLI — Claude Code executable (used by spawn script)

## Installation

Make scripts executable:
```bash
chmod +x claude_agents.py claude_talk.py claude_view.py claude_spawn.py
```

Add to your PATH (optional):
```bash
export PATH="$PATH:$HOME/tools/t-harness"
```

Then use from anywhere:
```bash
claude_spawn.py claude-builder builder ~/src/project
claude_agents.py json
claude_talk.py claude-builder "your message"
```
