# harness-marketplace

Claude Code marketplace for use with this harness.

## Plugins

| Plugin | Description |
|---|---|
| [manage-session](./plugins/manage-session/) | Coordinate multiple Claude Code agents running in tmux sessions using local Python helper scripts in the current working directory. Use when the user asks to spawn, list, message, delegate to, review with, or coordinate other Claude agents; when a task would benefit from separate builder, reviewer, security-reviewer, researcher, or tester agents; or when reporting status across active Claude tmux sessions. Prefer this skill over manual tmux commands for multi-agent coordination. |

## Adding this marketplace

In Claude Code, run:

```
/plugins marketplace add git@github.com:Nathanael-from-Security/t-harness.git
```

## Repository

`totara@totara.ghe.com:totara/xxx.git`


## Usage

### SRA Plugin

```
/manage-session:manage-session [WHAT_YOU_WANT_TO_MANAGE]
```