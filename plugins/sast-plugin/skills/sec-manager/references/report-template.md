# Consolidated Security Review: [scope]

**Date:** YYYY-MM-DD  
**Reviewer:** sec-manager skill  
**Source reports:**

- `security/red-team-report.md` (red-team agent, YYYY-MM-DD)
- `security/lint-task-report.md` (lint-task skill, deterministic rule pass, YYYY-MM-DD)
- `security/blue-team-report.md` (blue-team agent, code-level defensive scope, YYYY-MM-DD)

**Scope:** [as established by the source reports; call out disagreements]  
**Commit/branch:** [SHA or branch name if applicable]

## Executive Summary

[Write 5-8 sentences. Explain the unified posture across exploitability, code-level visibility, and deterministic coverage confidence. Include the most important sentence: if an attacker exploited the highest-severity findings today, what would they achieve, what would the application emit for downstream detection, and how broadly or confidently does lint-task confirm the weakness?]

[Include headline correlations and the top three prioritised actions. Note that operational defence is out of scope for all source reports and is addressed in Operational Defence Handoff. Do not include detailed finding evidence here.]

## Source Report Status

| Report | Present | Findings | Critical | High | Medium | Low | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| Red team | [Yes/No] | [n] | [n] | [n] | [n] | [n] | [...] |
| Lint-task deterministic pass | [Yes/No] | [n] | [n] | [n] | [n] | [n] | [Includes unit/rule coverage ledger or note missing coverage] |
| Blue team code-level review | [Yes/No] | [n] | [n] | [n] | [n] | [n] | [...] |

[If a report is missing, state what coverage is absent. Example: No lint-task report; deterministic rule coverage, unit/rule accounting, and confirmation of issue breadth are not represented in this consolidation.]

## Joint Findings

### Joint Finding J1: [Title summarising the consolidated issue]

- **Joint severity:** Critical / High / Medium / Low / Informational
- **Source findings:** R3 (red-team Critical), B2 (blue-team High), L4 (lint-task High)
- **Fingerprint:** `sql-injection:classes/handler/users_handler.php#users_handler::find_by_filter`
- **Affected:** `path/to/file.php:123-145`
- **Classification:** CWE-89, MITRE ATT&CK T1190, OWASP A03:2021

**Joint scenario**

[Explain how the source findings combine across the three axes. Be concrete.]

Example:

An unauthenticated attacker exploits the SQL injection at `path:line` (R3: exploitable). The application emits no event for raw-query usage on this path (B2: invisible to downstream detection). Lint-task independently records the same unsafe-query rule hit in this unit and two related units (L4: deterministic confirmation that the weakness is real and repeated).

**What each source contributes**

- **R3 (red-team):** [1-2 sentence exploitability summary. Full evidence and PoC remain in the source report.]
- **B2 (blue-team):** [1-2 sentence code-level visibility or exposure gap.]
- **L4 (lint-task):** [1-2 sentence deterministic rule hit, coverage impact, or repeated occurrence.]

**Consolidated remediation**

[Explain what fix closes all linked findings. If separate fixes are required, state the priority order.]

Example:

Parameterise the query at `app/db/users.php:47` first to remove the exploit path. Add structured audit emission for raw-query usage with the schema required by B2. Re-run lint-task and confirm the unsafe-query rule no longer triggers in the affected unit or related units.

**Validation**

[Describe how to confirm closure. Reference source reports' validation steps where possible.]

---

### Joint Finding J2: [Title]

[Repeat structure.]

## Single-Report Findings Not Correlated

Findings in this section appear in only one source report. They are not lower priority by default; they are simply not correlated across reports. Their original severity stands unless explicitly adjusted elsewhere.

Record the source-supplied fingerprint for each finding (or the source-supplied partial fingerprint with the unresolved component noted) using `references/fingerprinting-spec.md`.

### From red-team report

- **R1** [Critical] [title] - `file:line` - `broken-access-control:classes/external/manage_webhooks.php#manage_webhooks::execute` - see red-team report Findings section.
- **R2** [High] [title] - `file:line` - `<vuln-class>:<plugin-relative-path>#<symbol>` - see red-team report Findings section.

### From lint-task report

- **L1** [Medium] [title] - `file:line` - `<vuln-class>:<plugin-relative-path>#<symbol>` - see lint-task report Findings section.

### From blue-team report

- **B1** [Medium] [title] - `file:line` - `<vuln-class>:<plugin-relative-path>#<symbol>` - see blue-team report Findings section.

## Shared Root Causes

[Document findings across reports that trace to one architectural or process issue. Each entry should list the joint and single findings it explains, then identify the highest-leverage fix.]

Example:

**SRC1: Inconsistent authorization middleware.** R2, R5, B3, and B6 all stem from per-router authorization checks instead of a global policy decision point. Introduce framework-level authorization middleware and route-level policy declarations. Estimated effort: medium.

**SRC2: No central audit emission framework.** B1, B4, B7, plus the visibility components of J1 and J3, stem from ad-hoc logging in each module. Introduce a central audit framework with documented schema and per-module audit decorators. Estimated effort: large.

## Compensating Controls Identified

[Document controls or coverage boundaries that narrow risk. Credit the right source. Do not invent controls.]

- **Deterministic narrowing from lint-task:** [Example: R7 flagged reflected XSS in admin notes. L3 confirms the same rule hit only in one renderer rather than the whole subsystem.]
- **Code-level preventive controls or visibility from blue team:** [Example: B6 confirms session ID rotation on auth state change and audit emission of the rotation event.]
- **Red-team observations of existing controls:** [Example: red-team notes global CSRF middleware protects state-changing endpoints.]

## Contradictions Resolved

[Document disagreements between source reports and how they were resolved. If a spot-check was required, cite the inspected file and explain the resolution.]

Example:

R9 claimed `app/utils/path.py:47` is vulnerable to path traversal. B5 claimed the path is sanitised by middleware. Inspection of `app/middleware/path.py:23` confirmed sanitisation is correct for the attack class R9 described. R9 is downgraded to Informational; the middleware is the compensating control.

## Prioritised Action Plan

| # | Source | Fingerprint | Joint severity | Fix summary | Owner | Effort |
|---:|---|---|---|---|---|---|
| 1 | J3 | `sql-injection:classes/handler/users_handler.php#users_handler::find_by_filter` | Critical | Parameterise query | Backend | S |
| 2 | J1 | `csrf:classes/external/manage_webhooks.php#manage_webhooks::execute` | Critical | Add CSRF middleware globally | Backend | M |
| 3 | SRC1 | n/a (root cause) | High, closes R2, R5, B3, B6 | Introduce central auth middleware | Backend + Platform | L |
| 4 | SRC2 | n/a (root cause) | High, closes B1, B4, B7 | Central audit emission framework with documented schema | Backend + Platform | L |
| 5 | R1 | `broken-access-control:classes/external/manage_webhooks.php#manage_webhooks::execute` | High | [...] | [...] | [...] |

Order joint Criticals first, then high-leverage shared root causes, then joint Highs, then single-report Critical and High findings, then Mediums, Lows, and Informational items.

## Coverage Map Cross-Report

[Join red-team attack surface assessment, blue-team code-level emission status, and lint-task deterministic coverage results. Source rows from existing reports only.]

| Attack surface | Red team exploitability | Blue team code emission | Lint-task coverage confidence |
|---|---|---|---|
| Auth - credential stuffing | Vulnerable (R1) | Not emitted (B1) | Repeated auth-rule hits across login handlers (L2) |
| Auth - session fixation | Mitigated by rotation in code | Emits with sufficient context | No rule hit after deterministic pass |
| Input - SQL injection | Vulnerable (R3) | Not emitted on raw-query path (B2) | Unsafe-query rule confirmed in affected units (L4) |
| Output - reflected XSS | Vulnerable (R7) | Template path not emitted (B4) | Rule hit isolated to one renderer (L3) |

## Operational Defence Handoff

None of the source agents can assess operational defence unless relevant artifacts are present in the repository. This section is a handoff brief for a separate engagement covering SIEM rule firing, alert routing, runbook readiness, incident response rehearsal, on-call coverage, MFA enforcement at the IdP, backups, key rotation cadence, and operational metrics.

### Detection capabilities now feasible after remediation

[Aggregate from blue-team downstream handoff notes.]

Example:

After J1, J3, and SRC2 are remediated, the application will emit structured events sufficient for downstream detection rules such as:

- Credential stuffing: `event.action=login` and `event.outcome=failure`, grouped by `source.ip`, threshold 20 failures per 60 seconds.
- Bulk data export: `event.action=data.export` with `data.row_count > 10000` from non-batch contexts.
- Privilege escalation: `event.action=role.granted` where `target.role IN (admin, owner)` outside change windows.

### Detection capabilities still gapped after remediation

[List exploitable techniques that remain difficult to distinguish at application level and need host, network, WAF, RASP, third-party, or SIEM-layer detection.]

### Operational concerns flagged for separate review

- **SIEM rule existence and firing:** Verify in the SIEM or detection-as-code repository.
- **Alert routing:** Confirm rule severity maps to the right escalation path.
- **Runbooks:** Create or update runbooks for the scenarios surfaced by joint findings.
- **IR rehearsal:** Use the exploit chains documented in Joint Findings as tabletop scenarios.
- **MFA, IdP, backup, key rotation:** Confirm out of band; these were not assessable from repository-local reports.

## Strategic Recommendations

[Recommendations spanning all three lenses.]

Examples:

- Adopt a common application security event schema such as ECS or OCSF where appropriate.
- Integrate detection-as-code review alongside SAST in CI.
- Use lint-task coverage deltas as a release gate after security remediation.
- Schedule tabletop exercises using the chained scenarios from Joint Findings.
- Centralise audit emission and authorization policy enforcement.

## What This Consolidation Did Not Cover

- **Operational defence:** SIEM rule firing, alert routing, runbook readiness, IR rehearsal, MFA enforcement at the IdP, backup execution, key rotation cadence, and operational metrics.
- **Missing source reports:** [List any absent report and resulting coverage gap.]
- **Source-report out-of-scope domains:** [Carry forward relevant out-of-scope items from the source reports.]
- **Verification limits:** [List unresolved contradictions or spot-check limits.]
- **Source report gaps:** [Carry forward relevant What I Did Not Review sections from source reports.]
