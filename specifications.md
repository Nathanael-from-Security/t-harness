# T Harness — Specifications

## 1. Overview

T Harness is a wrapper around Claude Code that adds multi-agent orchestration, shared state, and autonomy controls. It does not replace Claude Code; it layers utilities on top of the existing `claude` CLI so that several Claude Code agents can run concurrently, coordinate, share memory, and operate unattended within defined safety limits.

The current implementation provides four tmux-based primitives:

- `claude_spawn.py` — create or attach to an agent session
- `claude_agents.py` — list active agent sessions
- `claude_talk.py` — send a message to an agent session
- `claude_view.py` — attach to or switch to an agent session

This document specifies the target system that builds on those primitives.

## 2. Goals and Non-Goals

### Goals

- Run multiple Claude Code agents concurrently in a single terminal via tmux.
- Allow agents to spawn, address, and coordinate with other agents.
- Provide shared task management across agents.
- Configure language servers (LSP) automatically per project.
- Ship reusable agent profiles that carry role context, tools, and configuration.
- Resolve user-input prompts automatically when the user is absent, within policy.
- Provide a shared, persistent memory graph accessible to all agents.
- Pause or throttle sessions automatically when token consumption exceeds a budget.

### Non-Goals

- Replacing or forking the Claude Code CLI.
- Building a graphical user interface. The harness is terminal-first.
- Acting as a hosted multi-user service. The harness targets a single operator on one machine.
- Managing remote or cloud execution. All sessions run on the local host.

## 3. Architecture

```
                         ┌──────────────────────────────┐
                         │           Operator            │
                         │      (single terminal)        │
                         └───────────────┬──────────────┘
                                         │ tmux client
                         ┌───────────────▼──────────────┐
                         │          tmux server          │
                         │  claude-planner               │
                         │  claude-builder               │
                         │  claude-reviewer              │
                         │  claude-security  ...          │
                         └───┬───────────┬───────────┬───┘
                             │           │           │
                    ┌────────▼──┐  ┌─────▼─────┐  ┌──▼────────┐
                    │ claude    │  │ claude    │  │ claude    │
                    │ (agent)   │  │ (agent)   │  │ (agent)   │
                    └────┬──────┘  └─────┬─────┘  └────┬──────┘
                         │               │             │
        ┌────────────────┴───────────────┴─────────────┴───────────────┐
        │                       Shared harness layer                     │
        │  Task store · Memory-graph MCP · Profiles · Hooks · Budget      │
        └────────────────────────────────────────────────────────────────┘
```

- Each agent is a standard `claude` process running inside a dedicated tmux session.
- Coordination occurs through harness CLIs (message passing) and shared state (task store, memory graph).
- Behavioral controls (budget pausing, auto-resolution) are enforced through Claude Code hooks configured by the harness.

### 3.1 Naming and Identity

- Session names use the prefix `claude-` (configurable via `CLAUDE_AGENT_PREFIX`).
- Each agent carries identity through environment variables set at spawn time:
  - `CLAUDE_AGENT_NAME` — agent role label
  - `CLAUDE_AGENT_SESSION` — tmux session name
  - `CLAUDE_AGENT_WORKDIR` — working directory
  - `CLAUDE_AGENT_ROLE` — explicit role; falls back to inference from session name
- Session name is the addressable identity. It must be unique per agent.

## 4. Components

| Component | Status | Description |
|-----------|--------|-------------|
| `claude_spawn.py` | Exists | Create or attach to an agent session; install keybinds; deliver intro briefing |
| `claude_agents.py` | Exists | List agent sessions in `table`, `json`, or `names` format |
| `claude_talk.py` | Exists | Send single-line or multiline messages to an agent session |
| `claude_view.py` | Exists | Attach to or switch the client to an agent session |
| `claude_tasks.py` | Planned | Task management CLI over a shared task store |
| `claude_profile.py` | Planned | Resolve and apply agent profiles at spawn time |
| `claude_lsp.py` | Planned | Detect project languages and configure LSP automatically |
| `claude_budget.py` | Planned | Track token usage and enforce budget thresholds |
| `claude_autoanswer.py` | Planned | Resolve user-input prompts when the operator is absent |
| Memory-graph MCP | Planned | MCP server exposing a shared knowledge graph |
| Hook scripts | Planned | Claude Code hooks wiring budget, auto-answer, and logging |

## 5. Feature Specifications

### 5.1 Cross-Agent Spawning

Agents and the operator can create new agents and coordinate with existing ones.

**Behavior**

- `claude_spawn.py <session-name> <agent-role> [workdir]` creates a new tmux session, sets identity environment variables, starts `claude`, and delivers an intro briefing.
- If the session already exists, the command attaches to it rather than creating a duplicate.
- The intro briefing instructs the agent how to spawn further agents and how to message peers, and forbids manual `tmux` or `claude code --agent` invocation.
- Spawned agents inherit no conversation state from the spawner; coordination is explicit through messaging and shared state.

**Constraints**

- Session name (first argument) must be unique. Reusing an existing session name attaches instead of spawning.
- Spawn depth and total concurrent agents are bounded by the budget controls in section 5.8.

**Interfaces**

- `claude_spawn.py <session-name> <agent-role> [workdir]`
- `claude_talk.py <session-name> "<message>"`
- `claude_agents.py [table|json|names]`

### 5.2 Multi-Session Handling in a Single Terminal

The operator manages all agents from one tmux client.

**Behavior**

- `claude_spawn.py` installs tmux keybindings on every invocation:
  - `Ctrl-b S` — interactive session picker
  - `Ctrl-b A` — prompt for a session name and switch to it
  - `Ctrl-b n` — switch to the next `claude-*` session
  - `Ctrl-b p` — switch to the previous `claude-*` session
- `claude_view.py <session-name>` attaches to a session, or switches the active client when already inside tmux.
- `claude_agents.py` provides the live roster, including role, status, and working directory.

**Requirements**

- Navigation must be limited to `claude-*` sessions so non-agent tmux sessions are not disturbed.
- Status detection must distinguish `active` from `dead` panes.

### 5.3 Task Management

A shared task store coordinates work across agents.

**Data model**

- A task store persists at `.t-harness/tasks.json` within the project working directory (configurable).
- Each task record contains:
  - `id` — stable unique identifier
  - `title` — short description
  - `description` — full detail
  - `status` — `pending`, `in_progress`, `blocked`, `done`, `cancelled`
  - `assignee` — agent session name or `unassigned`
  - `created_by` — session name of the creator
  - `depends_on` — list of task ids
  - `created_at` / `updated_at` — ISO 8601 timestamps

**Behavior**

- Agents create, claim, update, and complete tasks through `claude_tasks.py`.
- Assignment to an agent notifies that agent through `claude_talk.py`.
- Writes are atomic. Concurrent writers must not corrupt the store; the implementation uses file locking or a single-writer queue.

**Interfaces**

- `claude_tasks.py add --title <t> [--description <d>] [--assignee <session>] [--depends-on <id>...]`
- `claude_tasks.py list [--status <s>] [--assignee <session>] [--format table|json]`
- `claude_tasks.py claim <id> --assignee <session>`
- `claude_tasks.py update <id> --status <s>`
- `claude_tasks.py show <id>`

**Open question**

- Whether the task store should be a flat JSON file or an MCP server. The JSON file is the initial target for simplicity; an MCP front end may follow.

### 5.4 Automatic LSP Use

The harness configures language servers so agents receive accurate symbol, definition, and diagnostic information.

**Behavior**

- `claude_lsp.py` detects project languages from manifest and source files (for example `package.json`, `composer.json`, `pyproject.toml`, `go.mod`).
- For each detected language, the harness maps to a supported language server and verifies its presence on `PATH`.
- The harness writes the resolved LSP configuration into the project Claude Code settings so spawned agents use it automatically.
- Missing servers are reported with installation guidance rather than failing the spawn.

**Requirements**

- Detection must run at spawn time and be idempotent.
- Configuration must be scoped to the project, not the user global settings, unless the operator opts in.

**Open question**

- The exact mechanism by which Claude Code consumes LSP configuration must be confirmed against the installed Claude Code version before implementation.

### 5.5 Built-in Agent Profiles

Profiles package the context and configuration a role needs so agents start ready to work.

**Profile contents**

- `role` — canonical role name (`planner`, `builder`, `reviewer`, `security-reviewer`, `researcher`)
- `briefing` — role-specific system context delivered after spawn
- `model` — preferred model for the role
- `allowed_tools` / `denied_tools` — tool policy
- `mcp_servers` — MCP servers the role should load, including the memory graph
- `default_paths` — files or directories the role should read first
- `autonomy` — default auto-resolution policy (see section 5.7)
- `budget` — default token budget (see section 5.8)

**Behavior**

- Profiles are stored as files under `profiles/<role>.toml` (or `.yaml`).
- `claude_spawn.py` resolves the role to a profile, applies configuration, and includes the briefing in the intro message.
- The current role inference (from session name) remains as a fallback when no profile matches.

**Built-in roles**

- `planner` — decomposition and design; read-heavy; minimal write access.
- `builder` — implementation; full edit access within the working directory.
- `reviewer` — code review; read access plus comment and report output.
- `security-reviewer` — adversarial review; read access; structured findings output.
- `researcher` — investigation; web and documentation access.

### 5.6 Auto-Resolution of User-Input Questions

When the operator is absent, agents must not block indefinitely on questions.

**Behavior**

- The harness defines an autonomy mode: `interactive` (default), `assisted`, or `autonomous`.
- A Claude Code hook intercepts user-input prompts (for example `AskUserQuestion`).
- In `assisted` and `autonomous` modes, `claude_autoanswer.py` resolves the prompt by:
  1. Applying explicit per-profile defaults where the question matches a known decision.
  2. Otherwise delegating to a designated resolver agent that answers from policy and project context.
  3. Recording every auto-resolved answer to an audit log with the question, the chosen answer, and the rationale.
- Destructive or outward-facing actions are never auto-approved. Such prompts pause the session and notify the operator instead.

**Absence detection**

- Absence is determined by an explicit autonomy mode set by the operator, optionally combined with an idle timeout on operator input.

**Safety**

- Auto-resolution must default to the most conservative safe option when uncertain.
- All auto-resolved decisions require an audit entry for later operator review.

### 5.7 Memory-Graph MCP

A shared knowledge graph gives agents durable, queryable memory.

**Model**

- Entities, relations, and observations form a directed graph.
  - `entity` — a named node with a type (for example `service`, `decision`, `bug`, `person`).
  - `relation` — a typed directed edge between two entities.
  - `observation` — a timestamped fact attached to an entity.

**Behavior**

- The harness runs a memory-graph MCP server and registers it with agents through their profiles.
- Agents store findings, decisions, and context as entities and observations; they recall them by query before acting.
- Memory is shared across all agents in the project scope, enabling one agent to build on another's findings.

**Operations (MCP tools)**

- `create_entities`, `create_relations`, `add_observations`
- `delete_entities`, `delete_relations`, `delete_observations`
- `search_nodes`, `open_nodes`, `read_graph`

**Persistence**

- The graph persists under `.t-harness/memory/` scoped to the project.

**Constraints**

- Secrets, credentials, tokens, and third-party personal data must not be written to the graph.

### 5.8 Session Pausing on Excess Token Consumption

The harness enforces token budgets to prevent runaway cost.

**Behavior**

- Each session has a token budget, set by profile and overridable per spawn.
- A Claude Code hook reports token usage; `claude_budget.py` accumulates usage per session.
- Thresholds drive escalating responses:
  - At a soft threshold (for example 75 percent), warn the operator and the agent.
  - At a hard threshold (100 percent), pause the session by blocking further tool use through the hook and notifying the operator.
- A paused session resumes only on explicit operator action or a budget increase.

**Data**

- Per-session usage and budget persist under `.t-harness/budget/` so limits survive restarts.

**Interfaces**

- `claude_budget.py status [--session <name>]`
- `claude_budget.py set --session <name> --limit <tokens>`
- `claude_budget.py resume --session <name>`

**Constraints**

- Pausing must be enforced through hooks, not advisory text, so an agent cannot ignore the limit.
- Aggregate budget across all sessions should also be trackable to bound total cost.

## 6. Configuration

- Project-scoped harness state lives under `.t-harness/` in the working directory:
  - `tasks.json` — task store
  - `memory/` — memory graph
  - `budget/` — token usage and limits
  - `audit/` — auto-resolution and pause logs
- Role profiles live under `profiles/` in the harness repository.
- Environment variables:
  - `CLAUDE_AGENT_PREFIX` (default `claude-`)
  - `CLAUDE_BIN` (default `claude`)
  - `AGENTS_BIN`, `SEND_BIN` — helper script overrides used by `claude_spawn.py`
  - `CLAUDE_AGENT_NAME`, `CLAUDE_AGENT_SESSION`, `CLAUDE_AGENT_WORKDIR`, `CLAUDE_AGENT_ROLE`

## 7. Dependencies

- `tmux` — session management
- Python 3.6 or later — script runtime
- `claude` CLI — Claude Code executable
- Language servers — per detected project language (section 5.4)
- An MCP runtime for the memory-graph server (section 5.7)

## 8. Security and Safety Requirements

- Agents must not transmit secrets, credentials, API keys, tokens, or third-party personal data to other agents or into the memory graph unless explicitly authorized.
- Auto-resolution must never approve destructive or outward-facing actions automatically.
- Budget enforcement must be hook-backed and non-bypassable by the agent.
- All autonomous decisions and pauses must be auditable.
- Outputs produced under autonomous operation require operator review before any external use.

## 9. Phasing

| Phase | Scope |
|-------|-------|
| 1 (current) | tmux primitives: spawn, list, talk, view |
| 2 | Agent profiles and automatic LSP configuration |
| 3 | Task management CLI and shared task store |
| 4 | Memory-graph MCP integration |
| 5 | Budget tracking and hook-based session pausing |
| 6 | Auto-resolution of user-input prompts and autonomy modes |

## 10. Open Questions

- Task store backing: flat JSON file versus MCP server.
- Exact Claude Code hook events available for token reporting and prompt interception in the installed version.
- The mechanism by which Claude Code consumes externally supplied LSP configuration.
- Whether memory should be project-scoped only or also support a cross-project global graph.
- How autonomy modes interact with per-task overrides.
