---
name: moodle-security-triage
description: Triage a batch of Moodle security advisory Jira tickets against the Totara codebase and produce a patch-decision table. Invoke with one or more Jira ticket IDs or URLs, e.g. `/moodle-security-triage TL-49151 TL-49153`.
---

Triage a batch of Moodle security advisory Jira tickets against the Totara codebase and produce a patch-decision table.

Invoke with one or more Jira ticket IDs or URLs:
  `/moodle-security-triage TL-49151 TL-49153 TL-49154`
  `/moodle-security-triage https://totara.atlassian.net/browse/TL-49151`

## Prerequisites

- Atlassian Rovo MCP must be connected (`/mcp` → "claude.ai Atlassian Rovo").
- Working directory must be the Totara repository root (e.g. `/home/[user]/sites/txp-shared`).

---

## Steps

Run all steps that are independent of each other in parallel.

### Step 1 — Fetch Jira ticket titles

Use `mcp__claude_ai_Atlassian_Rovo__getJiraIssue` for each ticket ID (all in parallel).

- `cloudId`: `totara.atlassian.net`
- `fields`: `["summary"]`

Extract the ticket `summary` field as the title.

### Step 2 — Get the Moodle advisory URL

Each ticket description contains an advisory ID (e.g. `MSA-26-0029`) in the ticket summary.

Construct the canonical advisory page URL:
  `https://moodle.org/security/advisories/<MSA-ID>`

### Step 3 — Fetch MDL issue numbers and git commit search links

`WebFetch` all advisory pages in parallel:
  `https://moodle.org/security/advisories/<MSA-ID>`

Prompt: *"Extract all git.moodle.org links and any mention of affected files, MDL issue numbers, or components."*

Each page lists an MDL tracker number (e.g. `MDL-84535`) and a `git.moodle.org` search link. Capture the MDL number — it is the GitHub commit search key.

### Step 4 — Find the GitHub commit SHA

Search GitHub for each MDL number in parallel:
  `WebFetch https://github.com/moodle/moodle/search?q=<MDL-NUMBER>&type=commits`

Prompt: *"Return the full commit SHA hash and commit title for <MDL-NUMBER>."*

This returns the full 40-character SHA and a one-line commit message that names the affected component.

### Step 5 — Identify changed files

`WebFetch` each commit page in parallel:
  `https://github.com/moodle/moodle/commit/<FULL-SHA>`

Prompt: *"List all files changed in this commit. Return the full file paths."*

This gives the Moodle-relative file paths (e.g. `public/mod/assign/locallib.php`).

### Step 6 — Extract the key fix line

`WebFetch` each commit diff in parallel:
  `https://github.com/moodle/moodle/commit/<FULL-SHA>.diff`

Prompt: *"Return the single most important added line (starting with +) that summarises the security fix. One line only."*

### Step 7 — Check the local Totara repository

For each affected Moodle path, strip the `public/` prefix and search the local repo.

**Rules for mapping Moodle paths to Totara paths:**

| Moodle path prefix | Where to look in Totara |
|--------------------|------------------------|
| `public/mod/`      | `server/mod/`          |
| `public/group/`    | `server/group/`        |
| `public/admin/`    | `server/admin/`        |
| `public/mnet/`     | `server/mnet/`         |
| `public/reportbuilder/` | `server/reportbuilder/` (note: Totara has its own RB at `server/totara/reportbuilder/` — these are different) |
| `public/lib/`      | `server/lib/`          |

Use `find` to check whether the directory or file exists, then `grep` to confirm whether the specific vulnerable function or pattern is present and unpatched.

**Grep patterns by vulnerability type:**

- **Missing capability check**: grep for the function name; check if it opens with `require_capability(...)`.
- **Missing CSRF / sesskey**: grep for `confirm_sesskey\|require_sesskey` near the vulnerable action name (`optional_param('action_name', ...)`).
- **SSRF / URL validation**: grep for the validation helper name (e.g. `url_is_blocked`, `curl_security_helper`).

### Step 8 — Determine patch requirement

Apply this decision logic for each ticket:

| Condition | Decision |
|-----------|----------|
| Module directory does not exist in Totara | **No patch needed** — module absent |
| Totara uses a bespoke replacement (e.g. `totara/reportbuilder` vs `reportbuilder/`) | **No patch needed** — different codebase |
| File exists, vulnerable code absent (feature not present) | **No patch needed** — feature not implemented |
| File exists, fix already applied (key line present) | **No patch needed** — already patched |
| File exists, vulnerable code present, fix not applied | **Patch required** |

---

## Output format

Produce a single markdown table with these columns:

| Ticket | Title | Code Location | Key Fix Line | Local Path Found | Code change required |
|--------|-------|---------------|-------------|-----------------|----------------------|

- **Ticket**: Jira key as a link, e.g. `[TL-49151](https://totara.atlassian.net/browse/TL-49151)`
- **Title**: MSA ID and short description from the Jira summary
- **Code Location**: exactly one Moodle file path (strip `public/`) — one row per file
- **Key Fix Line**: The single added line from Step 6, in a code span
- **Local Path Found**: The deepest Totara path confirmed to exist, with ✓ or "not present"
- **Code change required**: One of **No patch needed** or **Patch required**, plus one sentence of reasoning

If a ticket affects multiple files, emit one row per file. Repeat the Ticket and Title cells on each row. The "Code change required" verdict applies to the ticket as a whole — repeat the same value on each row.

### Step 9 — Post results to Jira

After the output table is produced, post a comment to each Jira ticket using `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue`.

- `cloudId`: `totara.atlassian.net`
- `issueIdOrKey`: the ticket key (e.g. `TL-49151`)
- `body`: the comment content (see format below)

Run all comment posts in parallel.

**Comment format:**

```
**MSA Triage Result**

| Code Location | Key Fix Line | Local Path Found | Code change required |
| ------------- | ------------ | ---------------- | -------------------- |
| <value> | <value> | <value> | <value> |

_Reviewed by MSA triage skill — <date>_
```

Use standard Markdown (Jira renders this format natively). Wrap the Key Fix Line value in backticks.

Only post to tickets that were successfully triaged (i.e. have a row in the output table). If a comment post fails for one ticket, continue posting to the remaining tickets and note the failure at the end of your response.

---

## Notes for repeated runs

- Moodle forum URLs (`/mod/forum/discuss.php?d=...`) return 403 without login. Always use `moodle.org/security/advisories/<MSA-ID>` instead.
- GitHub short SHAs (7 chars) sometimes 404 — always fetch the full 40-char SHA from the search page first.
- `gh` CLI is not available in this environment; use `WebFetch` on GitHub URLs and `Bash` with `find`/`grep` for local repo checks.
- Totara's `server/totara/reportbuilder/` is an entirely independent implementation of report builder; Moodle's `public/reportbuilder/` fixes do not apply to it.
- MNet (`mnet/`) is not present in this Totara codebase.
- All WebFetch and Jira calls that are independent should be issued in parallel to keep run time low.
