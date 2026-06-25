---
name: manage-session
description: Coordinate multiple Claude Code agents running in tmux sessions using local Python helper scripts in the current working directory. Use when the user asks to spawn, list, message, delegate to, review with, or coordinate other Claude agents; when a task would benefit from separate builder, reviewer, security-reviewer, researcher, or tester agents; or when reporting status across active Claude tmux sessions. Prefer this skill over manual tmux commands for multi-agent coordination.
---

# Agent Coordination

Use this skill to coordinate multiple Claude Code agents running in tmux sessions.

The coordination helpers are Python scripts located in the current working directory:

* `./claude_spawn.py` — create or attach to Claude agents in tmux sessions
* `./claude_talk.py` — send messages to agents by tmux session name
* `./claude_agents.py` — list active agents

Use these scripts instead of manual tmux commands.

## Core Rules

* Use the helper scripts in the current directory.
* Do not use `claude code --agent`.
* Do not create, rename, kill, or switch tmux sessions manually unless explicitly instructed by the user.
* Use tmux session names when messaging agents, not role names.
* Make session names unique.
* Prefer session names that start with `claude-`, such as:

  * `claude-builder`
  * `claude-reviewer`
  * `claude-security`
  * `claude-tester`
  * `claude-researcher`
* Include your own agent name and tmux session name when messaging another agent, if known.
* Keep messages specific, bounded, and actionable.
* Do not send secrets, credentials, API keys, tokens, private keys, cookies, personal data, customer data, or sensitive project material to another agent unless the user explicitly authorizes it.
* Before delegating work that may modify files, specify the expected scope and any files or directories that are off limits.
* Before asking another agent to run destructive commands, require confirmation from the user.

## Available Commands

### List active agents

Run:

```bash
./claude_agents.py
```

Use this before messaging an agent when the available sessions are unknown.

Use this to verify that a newly spawned agent exists.

### Spawn or attach to an agent

Run:

```bash
./claude_spawn.py <SESSION_NAME> <AGENT_ROLE> [workdir]
```

Arguments:

* `<SESSION_NAME>`: unique tmux session name to create or attach to
* `<AGENT_ROLE>`: role or purpose for the agent
* `[workdir]`: optional working directory; use `$PWD` when coordinating within the current repository

Correct examples:

```bash
./claude_spawn.py claude-builder builder "$PWD"
./claude_spawn.py claude-reviewer reviewer "$PWD"
./claude_spawn.py claude-security security-reviewer "$PWD"
./claude_spawn.py claude-tester tester "$PWD"
```

Do not reuse the same session name for a different role. For example, do not run:

```bash
./claude_spawn.py claude-builder reviewer "$PWD"
```

That may attach to the existing `claude-builder` session instead of creating a reviewer.

### Send a single-line message

Run:

```bash
./claude_talk.py <session-name> "<message>"
```

Example:

```bash
./claude_talk.py claude-reviewer "From claude-orchestrator: Please review the current diff for correctness, edge cases, and test gaps. Report findings only; do not modify files."
```

### Send a multiline message

Run:

```bash
cat <<'MSG' | ./claude_talk.py <session-name>
message here
MSG
```

Example:

```bash
cat <<'MSG' | ./claude_talk.py claude-security
From claude-orchestrator in session claude-orchestrator.

Please review the current diff for security issues. Focus on:
- authentication and authorization
- input validation
- injection risks
- secret handling
- unsafe file, shell, network, or deserialization behavior

Do not modify files. Return prioritized findings with file paths and recommended fixes.
MSG
```

## When to Coordinate

Use another agent when parallel or independent analysis would materially improve the result.

Good coordination cases:

* Delegating implementation while retaining orchestration
* Requesting review of a diff
* Requesting security analysis
* Asking a tester agent to design or run tests
* Asking a researcher agent to inspect documentation or existing code patterns
* Splitting a large task into bounded components
* Asking another agent for context from its own session

Avoid spawning agents for trivial tasks, small edits, or work that would be faster and clearer to do directly.

## Recommended Agent Roles

### Builder

Use a builder agent for implementation.

Suggested session name:

```text
claude-builder
```

Suggested role:

```text
builder
```

Suggested prompt:

```bash
cat <<'MSG' | ./claude_talk.py claude-builder
From <your-agent-name> in session <your-session-name>.

Task: implement the requested change.

Scope:
- Work only in the relevant files for this task.
- Keep the change minimal.
- Preserve existing behavior unless the task requires changing it.
- Add or update tests where appropriate.

Before starting, inspect the repository and report your plan.
After finishing, report changed files, tests run, and any unresolved risks.
MSG
```

### Reviewer

Use a reviewer agent for correctness, maintainability, and test coverage review.

Suggested session name:

```text
claude-reviewer
```

Suggested role:

```text
reviewer
```

Suggested prompt:

```bash
cat <<'MSG' | ./claude_talk.py claude-reviewer
From <your-agent-name> in session <your-session-name>.

Please review the current diff.

Focus on:
- correctness
- edge cases
- regressions
- maintainability
- test coverage
- unclear or unnecessary complexity

Do not modify files. Return findings grouped by severity, with file paths and concrete recommendations.
MSG
```

### Security Reviewer

Use a security reviewer agent for auth, crypto, parsing, network, shell, filesystem, dependency, or data-handling changes.

Suggested session name:

```text
claude-security
```

Suggested role:

```text
security-reviewer
```

Suggested prompt:

```bash
cat <<'MSG' | ./claude_talk.py claude-security
From <your-agent-name> in session <your-session-name>.

Please perform a security review of the current diff.

Focus on:
- authentication and authorization bypass
- injection vulnerabilities
- unsafe shell execution
- path traversal
- unsafe deserialization
- SSRF or unsafe network access
- secret leakage
- insecure cryptography
- dependency or supply-chain risk
- logging of sensitive data

Do not modify files. Return prioritized findings with exploitability, impact, affected files, and recommended remediations.
MSG
```

### Tester

Use a tester agent to identify and run relevant tests.

Suggested session name:

```text
claude-tester
```

Suggested role:

```text
tester
```

Suggested prompt:

```bash
cat <<'MSG' | ./claude_talk.py claude-tester
From <your-agent-name> in session <your-session-name>.

Please identify and run the relevant tests for the current change.

Focus on:
- the smallest useful test set first
- failing tests related to the change
- missing test coverage
- reproducible commands

Do not make broad code changes. If a test fails, report the command, failure summary, and likely cause.
MSG
```

### Researcher

Use a researcher agent to inspect repository conventions, internal docs, or unfamiliar areas of the codebase.

Suggested session name:

```text
claude-researcher
```

Suggested role:

```text
researcher
```

Suggested prompt:

```bash
cat <<'MSG' | ./claude_talk.py claude-researcher
From <your-agent-name> in session <your-session-name>.

Please research the relevant codebase context for this task.

Find:
- existing patterns
- related files
- similar implementations
- tests that cover nearby behavior
- constraints or conventions we should preserve

Do not modify files. Return a concise summary with file paths and recommendations.
MSG
```

## Coordination Workflow

When coordinating multi-agent work:

1. List active agents if session state is unknown.

   ```bash
   ./claude_agents.py
   ```

2. Spawn any missing agents with clear session names.

   ```bash
   ./claude_spawn.py claude-reviewer reviewer "$PWD"
   ```

3. Send each agent a bounded task.

   ```bash
   cat <<'MSG' | ./claude_talk.py claude-reviewer
   From <your-agent-name> in session <your-session-name>.

   Please review the current diff. Do not modify files.
   MSG
   ```

4. Continue your own work while agents investigate.

5. Ask agents for status only when needed.

6. Integrate their findings critically. Do not blindly apply another agent's recommendation.

7. Report which agents were used and summarize their outputs.

## Message Format

Prefer this format when messaging another agent:

```text
From <agent-name> in session <session-name>.

Task:
<one clear task>

Context:
<minimal context needed>

Scope:
<allowed files, directories, or actions>

Constraints:
<do not modify files, do not run destructive commands, avoid secrets, etc.>

Expected output:
<report format, files changed, tests run, risks, etc.>
```

## Safety Requirements

Do not send sensitive information to another agent unless explicitly authorized by the user.

Sensitive information includes:

* API keys
* access tokens
* refresh tokens
* private keys
* passwords
* cookies
* session identifiers
* database credentials
* cloud credentials
* `.env` contents
* kubeconfigs
* SSH keys
* customer data
* personal data
* proprietary material outside the task scope

When in doubt, redact.

Use placeholders such as:

```text
<REDACTED_TOKEN>
<REDACTED_SECRET>
<CUSTOMER_DATA_REDACTED>
```

## Destructive or Risky Actions

Do not ask another agent to run destructive commands without user approval.

Risky actions include:

* deleting files
* force-pushing
* rewriting git history
* changing production configuration
* rotating secrets
* modifying infrastructure
* running migrations
* changing permissions
* killing processes
* removing tmux sessions
* making network calls to production systems

For risky work, ask the user first or request a dry-run plan from the agent.

## Git and File Modification Rules

When delegating to another agent:

* Say whether it may modify files.
* Say whether it may run tests.
* Say whether it may create commits.
* Prefer no commits unless the user explicitly requested commits.
* Require a summary of changed files and commands run.
* Require the agent to report any skipped tests or unresolved failures.

Default delegation policy:

```text
You may inspect files and run non-destructive commands.
Do not commit changes.
Do not push.
Do not modify files unless this task explicitly asks you to implement changes.
```

## Status Requests

Use status requests sparingly.

Example:

```bash
./claude_talk.py claude-builder "From claude-orchestrator: Please send a brief status update: current task, files touched, blockers, and next step."
```

## Completion Reports

When an agent completes work, ask for:

```text
- Summary
- Files changed
- Tests run
- Results
- Risks or follow-ups
```

Example:

```bash
./claude_talk.py claude-builder "From claude-orchestrator: Please provide a completion report with summary, files changed, tests run, results, and unresolved risks."
```

## Troubleshooting

If a script is missing or not executable, check the current directory:

```bash
ls -la
```

If the scripts exist but are not executable, ask the user before changing permissions. If approved, run:

```bash
chmod +x ./claude_spawn.py ./claude_talk.py ./claude_agents.py
```

If no agents are listed, run:

```bash
./claude_agents.py
```

Then spawn the required agent:

```bash
./claude_spawn.py claude-reviewer reviewer "$PWD"
```

If messaging fails, verify the exact session name:

```bash
./claude_agents.py
```

Then retry with the session name from the list.

## Preferred Defaults

Use these defaults unless the user gives different instructions:

* Working directory: `$PWD`
* Orchestrator session: `claude-orchestrator`
* Builder session: `claude-builder`
* Reviewer session: `claude-reviewer`
* Security reviewer session: `claude-security`
* Tester session: `claude-tester`
* Researcher session: `claude-researcher`

## Final Response Expectations

When this skill was used, include a concise coordination summary in the final response:

```text
Coordination used:
- claude-builder: implemented <summary>
- claude-reviewer: reviewed <summary>
- claude-security: found <summary>

Result:
<final outcome>

Tests:
<commands and results>

Risks:
<remaining risks or none>
```

Do not expose raw inter-agent chatter unless the user asks for it. Summarize relevant findings.
