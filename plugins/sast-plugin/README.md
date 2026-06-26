# SAST Plugin - Security Analysis Agent & Skills

A comprehensive **Static Application Security Testing (SAST)** plugin for Totara LMS providing multi-lens security analysis through coordinated offensive, defensive, and deterministic scanning agents. Built on the MCP (Model Context Protocol) framework for modular, composable security review workflows.

---

## Overview

This plugin orchestrates three specialized security review lenses to produce a consolidated, exploitability-aware security assessment:

1. **Red-Team (Offensive)** — Adversarial code review targeting real attack vectors
2. **Blue-Team (Defensive)** — Code-level defensive coverage analysis for detection capability  
3. **Lint-Task (Deterministic)** — Rule-by-rule verification of security pattern compliance
4. **Sec-Manager (Consolidation)** — Synthesizes all three reports into a prioritized review with exploit-chain analysis

---

## Quick Start

### Run a Full Security Review

Use `run_sec_manager_scan.sh` to run all three lenses and produce the consolidated review in one command:

```bash
./run_sec_manager_scan.sh /path/to/repo
```

The script:
1. Creates a source snapshot of the target path (excluding `.git`, `node_modules`, etc.)
2. Runs red-team, lint-task, and blue-team sequentially using `claude-opus-4-8`
3. Consolidates all three reports using `claude-haiku-4-5`

Reports are written to a timestamped directory:
```
/tmp/sec-agent/security/<timestamp>/
├── red-team-report.md
├── lint-task-report.md
├── blue-team-report.md
└── consolidated-review.md
```

Logs (including token usage and cost) are written to `/tmp/sec-agent/security/<timestamp>/logs/`.

To monitor progress while the scan runs:
```bash
watch -n 2 'ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd | grep "[c]laude"'
```
---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Nathanael-from-Security/sast-agent.git
   cd sast-agent
   ```

2. **Open Claude CLI:**
   Launch the Claude CLI on your system (or use an existing session).

3. **Register the plugin:**
   ```bash
   /plugin add ~/PATH/TO/THE/CLONED/REPO
   ```
   Replace `~/PATH/TO/THE/CLONED/REPO` with the actual path to your cloned repository (e.g., `~/projects/sast-agent`).

4. **Verify successful installation:**
   You should see a success message indicating that the plugin has been registered. The message will confirm the plugin is now available for use.

5. **Plugin location:**
   Once installed, the plugin tools are stored at:
   ```
   ~/.claude/plugins/_direct/sast-plugin/
   ```
   This directory contains:
   - `agents/` — Agent definitions (sec-manager, etc.)
   - `skills/` — Security review skills (red-team, blue-team, lint-task, sec-manager)
   - `task.py` — Task queue manager for rule-based scanning
   - `fingerprint.py` — Deterministic PHP finding fingerprint generator

---

## Architecture

### Plugin

We are leveraging a Claude plugin to wrap agent, skills and tools (scripts) all in one. This allows easy transfer and installation of a variety of files used by the Claude CLI.

### Agents

#### 1. **sec-manager** (`agents/sec-manager.agent.md`)
Consolidation agent that synthesizes red-team, blue-team, and lint-task reports into a prioritized, exploit-aware security review.

**Responsibilities:**
- Discover and validate prerequisite reports
- Generate missing reports (red-team → blue-team → lint-task order)
- Build finding correspondence map across all three lenses
- Identify exploit chains that cross report boundaries
- Perform joint severity calibration
- Detect shared root causes
- Resolve contradictions between reports
- Produce operational defence handoff brief

**Key Methodology:**

1. **Correspondence Mapping** — Find matches by:
   - Fingerprint overlap (primary key — same `{vuln-class}:{plugin-relative-path}#{symbol}`, or same path/symbol with a related class)
   - File path/line overlap
   - Semantic overlap (same attack pattern, different names)
   - Component overlap (same subsystem, different angles)

2. **Exploit Chain Synthesis** — Connect across reports:
   - Red team: "This exploit exists"
   - Blue team: "Application emits nothing useful for detection"
   - Lint-task: "Rule violation confirmed, repeated across units"
   - **Result:** Exploitable, hard to detect, systematically repeated

3. **Joint Severity Calibration** — Assess across three axes:
   - **Exploitability** (red-team perspective)
   - **Code-level visibility** (blue-team perspective — does app emit useful telemetry?)
   - **Deterministic confidence** (lint-task perspective — how widespread is the issue?)

4. **Root Cause Clustering** — Group findings by shared architectural decisions

5. **Contradiction Resolution** — Spot-check code when reports disagree

**Output Contract:**
- Preserves source finding identifiers (R*, B*, L*)
- Assigns each finding a stable fingerprint (`{vuln-class}:{plugin-relative-path}#{symbol}`)
- Includes file:line references
- Structured finding correspondence table (keyed on fingerprint)
- Exploit-chain analysis
- Prioritized remediation plan (grouped by root cause)
- Operational Defence Handoff section (downstream requirements)

**Prerequisite Report Requirements:**
- `security/red-team-report.md` — Offensive findings
- `security/blue-team-report.md` — Defensive code gaps
- `security/lint-task-report.md` — Deterministic rule coverage

If any report is missing, sec-manager generates it automatically.

---

### Skills

#### 1. **Red-Team Skill** (`skills/red-team/SKILL.md`)
Adversarial code review identifying real attack vectors.

**Focus Areas:**
- **Authentication:** Password storage, brute force protection, token entropy, MFA bypass, OIDC flaws
- **Authorization:** IDOR, vertical/horizontal privilege escalation, missing state-change checks
- **Injection:** SQL, NoSQL, command, LDAP, template, XXE, path traversal, SSRF
- **Output:** XSS (reflected/stored/DOM), open redirects, CSRF, clickjacking
- **Cryptography:** Weak algorithms, weak PRNGs, IV/nonce reuse, missing authentication
- **Secrets:** Hardcoded credentials, `.env` files, secrets in logs
- **Data exposure:** Excess response data, unencrypted PII, logs with sensitive fields
- **Race conditions:** TOCTOU, double-spend, session races

**Output:** `security/red-team-report.md` with exploitation scenarios and concrete proof-of-concept steps.

---

#### 2. **Blue-Team Skill** (`skills/blue-team/SKILL.md`)
Code-level defensive review assessing detection capability.

**Focus Areas:**
- **Authentication telemetry:** Login events with source IP, user agent, failure reason, correlation ID
- **Authorization audit:** Access decisions with context, denial reasons
- **Privileged action logging:** Admin actions, role changes, sensitive operations
- **Sensitive data access:** Who accessed what, when, from where
- **Input validation telemetry:** What inputs were rejected, why
- **Error handling:** Information disclosure in error responses/logs
- **Secrets hygiene:** Logs/responses not leaking credentials, tokens, PII

**Scope:** Application code, config files in repo, detection artefacts (if present)

**Out of Scope:** SIEM rule execution, alert routing, operational defence posture (requires systems outside repo)

**Output:** `security/blue-team-report.md` with code-level visibility gaps and detection recommendations.

---

#### 3. **Lint-Task Skill** (`skills/lint-task/SKILL.md`)
Deterministic rule-by-rule verification pass assessing security pattern compliance.

**Purpose:** Post-review verification that red-team and blue-team findings are rule-confirmed, repeated across units, or coverage-bounded.

**Approach:**
- Apply each rule deterministically to the codebase
- Record coverage counts and hit patterns
- Identify where violations cluster (systemic) vs. isolated
- Confirm exploit paths with measurable confidence

**Output:** `security/lint-task-report.md` with coverage tables and rule-confirmation ledger.

---

#### 4. **SAST Finding Format Skill** (`skills/sast-finding-format/SKILL.md`)
Standardizes vulnerability reporting across all three lenses.

**Ensures:**
- Each finding is a reachable, real vulnerability
- Correct severity level assignment
- All required fields populated (Issue, Evidence, Risk, Testing, Fix)
- No hallucinated or theoretical findings
- Proper deduplication
- Consistent grouping and summary structure

---

### Standalone Tools

#### `fingerprint.py` — Finding Fingerprint Generator

Builds a stable, deterministic fingerprint for a PHP finding from a vulnerability class, file path, and line number. Used by all three lenses to share a consistent identity for the same code location.

**Format:** `{vuln-class}:{plugin-relative-path}#{symbol}`

**Example output:**
```text
sql-injection:classes/handler/totara_webhook_handler_factory.php#totara_webhook_handler_factory::create_instance
```

**Usage:**
```bash
python fingerprint.py --plugin-root /path/to/plugin --vuln-class sql-injection \
  --path classes/handler/file.php --line 52 [--json]
```

**Arguments:** `--vuln-class` (required), `--path` (required), `--line` (required), `--plugin-root` (default: `server/totara/webhook`), `--json` (structured output).

**Symbol resolution:** Methods → `ClassName::methodName`; free functions → `functionName`; unnamed constructs fall back to nearest named ancestor; file-scope code uses `<setup>`, `<script>`, etc. Full rules: `skills/sec-manager/references/fingerprinting-spec.md`.

**Multi-location findings:** One fingerprint per location, grouped under the same finding ID.

**Validation:** `python -m pytest tests/fingerprint_test.py -q`

The fingerprint supplements source IDs (R*, B*, L*) — both are carried through reports. Partial fingerprints are recorded when path or symbol is unresolved.

---

#### `task.py` — Task Queue Manager

A simple file-backed task queue system for orchestrating iterative scanning workflows.

**Purpose:** Maintain a queue of security rules/checks to be applied to each analysis unit, tracking progress and preventing duplicate work.

**Functionality:**

```bash
# Initialize a new task queue from security rules
python task.py --f SCANNER_FILE

# Get the next task from the latest run (and remove it from queue)
python task.py --f SCANNER_FILE --get

# Start a fresh timestamped queue (reload from rules.md)
python task.py --f SCANNER_FILE --start

# Get the next task from a specific timestamped run
python task.py --f SCANNER_FILE --run-id 20260528T205222222872Z --get
```

**How It Works:**

1. **Rules source:** Reads from `/home/nathrais/tools/sast-plugin/data/rules.md`
2. **Storage:** Maintains task lists under `/tmp/tasklists/TIMESTAMP/FILENAME/tasks.txt`
3. **Queue operations:**
   - Initialize: Load all rules into a new timestamped queue
   - Get next: Return first task and remove it from queue under a lock
   - Start: Create a fresh timestamped queue from rules.md
   - Run ID: Use the printed timestamp with `--run-id` to avoid latest-pointer collisions in concurrent runs

**Usage Example (in sast-agent workflow):**

```bash
# Step 1: Initialize queue with all security rules for this unit
python ~/.claude/plugins/_direct/sast-plugin/task.py --f SCANNER_FILE
# Save the printed "Run ID: ..." value for strict isolation.
RUN_ID=20260528T205222222872Z

# Step 2: Iteratively process each rule
while true; do
    RULE=$(python ~/.claude/plugins/_direct/sast-plugin/task.py --f SCANNER_FILE --run-id "$RUN_ID" --get)
    if [ "$RULE" == "All tasks completed" ]; then
        break
    fi
    # Apply $RULE to current analysis unit
done
```

**Files Modified:**
- Temporary state: `/tmp/tasklists/TIMESTAMP/FILENAME/tasks.txt` (one task per line, removed after processing)
- Never modifies source code or reports

---

## Integration Flow

### How Sec-Manager Orchestrates the Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SEC-MANAGER ENTRY                           │
│                  (Consolidation Agent)                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ├─ PATHWAY VALIDATION
                              │  └─ security/ directory exists?
                              │
                    ┌─────────┴─────────┐
                    │                   │
        ┌───────────▼──────────┐   ┌────▼────────────────┐
        │ DISCOVER REPORTS     │   │ CHECK PREREQUISITES │
        │ • red-team-report.md │   │ • red-team?         │
        │ • blue-team-report   │   │ • blue-team?        │
        │ • lint-task-report   │   │ • lint-task?        │
        └──────────────────────┘   └────┬─────────────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                 MISSING? ═════════════════════════════ NO
                        │               │               │
                        YES             │           ┌───▼────────────────┐
                        │               │           │ LOAD ALL REPORTS   │
        ┌───────────────┴────────┐      │           │ • Parse red-team   │
        │ GENERATE MISSING       │      │           │ • Parse blue-team  │
        │ REPORTS IN ORDER:      │      │           │ • Parse lint-task  │
        │ 1. red-team-report     │      │           └───┬────────────────┘
        │    (run red-team       │      │               │
        │     skill)             │      │               │
        │ 2. blue-team-report    │      │               │
        │    (run blue-team      │      │               │
        │     skill)             │      │               │
        │ 3. lint-task-report    │      │               │
        │    (run lint-task      │      │               │
        │     skill)             │      │               │
        └────────────┬───────────┘      │               │
                     └──────────────────┴───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  SYNTHESIZE        │
                    ├────────────────────┤
                    │ 1. Find Correspond │
                    │    Map findings    │
                    │ 2. Trace Chains    │
                    │    Exploit paths   │
                    │ 3. Joint Severity  │
                    │    Calibrate risk  │
                    │ 4. Root Causes     │
                    │    Group by fix    │
                    │ 5. Contradictions  │
                    │    Spot-check code │
                    │ 6. Ops Defence     │
                    │    Handoff brief   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │  OUTPUT CONSOLIDATED       │
                    │  REVIEW                    │
                    │ security/consolidated-     │
                    │ review.md                  │
                    └────────────────────────────┘
```

---

### Skill Invocation Sequence

**For Missing Prerequisites (if any):**

```
RED-TEAM SKILL
│
├─ Read ~/.claude/plugins/_direct/sast-plugin/skills/red-team/SKILL.md
├─ Scan repository for adversarial vectors
├─ Identify real attack paths
└─ Write security/red-team-report.md

BLUE-TEAM SKILL
│
├─ Read ~/.claude/plugins/_direct/sast-plugin/skills/blue-team/SKILL.md
├─ Analyze code-level defensive coverage
├─ Assess detection telemetry gaps
└─ Write security/blue-team-report.md

LINT-TASK SKILL
│
├─ Read ~/.claude/plugins/_direct/sast-plugin/skills/lint-task/SKILL.md
├─ Apply deterministic rules post-review
├─ Confirm violations & coverage
└─ Write security/lint-task-report.md
```

**For Consolidation:**

```
SEC-MANAGER SKILL
│
├─ Read ~/.claude/plugins/_direct/sast-plugin/skills/sec-manager/SKILL.md
├─ Load all three prerequisite reports
├─ Fingerprint every finding ({vuln-class}:{plugin-relative-path}#{symbol})
├─ Build correspondence map (fingerprint/file/semantic/component overlap)
├─ Identify exploit chains across reports
├─ Calibrate joint severity (exploitability × visibility × determinism)
├─ Cluster by root cause
├─ Resolve contradictions
├─ Aggregate operational defence handoff
└─ Write security/consolidated-review.md
```

---

## Data References

### Context & Rules

- **`data/context.md`** — Totara security model, safe patterns, per-category heuristics
- **`data/rules.md`** — Security rules loaded by task.py for iterative scanning

These files provide domain-specific knowledge for Totara:
- Safe input validation patterns (`required_param`, `optional_param`)
- Authorization patterns (`require_login`, `require_capability`)
- Database access patterns (DML parameterization)
- Output escaping functions
- CSRF token handling

---

## Output Structure

After a complete scan, the `security/` directory contains:

```
security/
├── red-team-report.md           # Offensive findings (R001, R002, ...)
├── blue-team-report.md          # Defensive gaps (B001, B002, ...)
├── lint-task-report.md          # Deterministic rule hits (L001, L002, ...)
└── consolidated-review.md       # Synthesized findings with exploit chains
```

### Consolidated Review Structure

```markdown
# Consolidated Security Review: [scope]

- Executive Summary
  - Finding Correspondence Map (R*, B*, L* cross-references)
  - Exploit Chains (multi-report correlations)
  - Root Cause Analysis
  
- Consolidated Findings (by joint severity; each finding carries its fingerprint and source IDs)
  - Critical
  - High
  - Medium
  - Low
  - Informational

- Remediation Roadmap (grouped by root cause)

- Operational Defence Handoff
  - Detection recommendations
  - Alert rule requirements
  - IR runbook requirements
  - Follow-on assessment needs
```

---

## Contributing

### Adding New Security Rules

1. Edit `data/rules.md`
2. Add rule in format: `CATEGORY: <rule description>`
3. task.py will automatically load new rules on next `--start` invocation

### Extending for New Platforms

1. Create new agent: `agents/YOUR_AGENT.agent.md`
2. Add platform-specific context to `data/context.md`
3. Add platform-specific skills under `skills/`
4. Update `plugin.json`

---

## Support & References

- **Totara Docs:** See `instructions/` directory for Totara conventions, architecture, testing guidelines
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **CWE Top 25:** https://cwe.mitre.org/top25/
- **MITRE ATT&CK:** https://attack.mitre.org/
- **Sigma Rules:** https://github.com/SigmaHQ/sigma
