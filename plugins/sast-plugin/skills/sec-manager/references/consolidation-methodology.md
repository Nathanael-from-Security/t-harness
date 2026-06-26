# Consolidation Methodology

Use this reference when consolidating completed red-team, blue-team, and lint-task security review reports.

## Purpose

Produce synthesis, not a fourth review. Read the source reports, identify relationships between findings, and produce one prioritised security review that is more useful than the individual reports alone.

The value is in correlations:

- Offensive exploitability joined to code-level visibility gaps.
- Deterministic rule confirmation joined to exploitability.
- Shared root causes across multiple source findings.
- Exploit chains that cross report boundaries.
- Compensating controls and coverage boundaries that narrow severity or scope.

## Inputs

Expected reports are usually under `security/`:

- `security/red-team-report.md` or similar.
- `security/lint-task-report.md` or similar.
- `security/blue-team-report.md` or similar.

If names vary, inspect `security/*.md` and identify report type from headings and structure.

If one report is missing, continue with available reports and mark the missing coverage explicitly. If no source reports are available, stop and ask the dispatcher to provide or generate at least one report.

## Report Type Contributions

### Red-team report

Contributes offensive review and exploitability assessment from code and configuration.

Use it for:

- Attack path evidence.
- Exploitability constraints.
- Existing preventive controls observed during attack analysis.
- CWE, MITRE ATT&CK, OWASP, or similar classification already present in the report.

### Blue-team report

Contributes code-level defensive visibility review.

Use it for:

- Whether security-relevant events are emitted.
- Whether emitted events contain enough context for downstream investigation.
- Whether logs, audit records, or responses leak secrets, PII, or sensitive implementation detail.
- Code-level preventive controls and emissions that make residual attacks visible.
- Downstream handoff notes for detection and response teams.

Do not treat the blue-team report as proof that SIEM rules exist or fire. It only assesses repository-resident code and configuration.

### Lint-task report

Contributes deterministic rule-by-rule verification and coverage signals.

Use it for:

- Rule-confirmed findings.
- Unit, file, or component coverage ledgers.
- Evidence that a weakness is repeated, isolated, absent, or coverage-bounded.
- Residual rule gaps after deterministic scanning.

Do not treat lint-task output as complete exploitability proof unless the report explicitly establishes that.

## Workflow

1. Read all available reports end-to-end.
2. Build a source finding index using the fingerprints already supplied by red-team, blue-team, and lint-task. Validate and preserve those fingerprints; do not make consolidation the first place fingerprints are created.
3. Build a finding correspondence map keyed on the fingerprint.
4. Identify exploit chains.
5. Identify confirming evidence, compensating controls, and coverage boundaries.
6. Identify shared root causes.
7. Resolve contradictions.
8. Compute joint severity using `severity-rubric.md`.
9. Aggregate blue-team downstream handoff content and lint-task coverage signals.
10. Build the prioritised remediation plan.
11. Write the final report using `report-template.md`.
12. Check the final report against `discipline-rules.md` before returning it.

## Finding Index

For each source finding, capture:

- Source report: red-team, blue-team, or lint-task.
- Finding identifier: for example R1, B3, L2.
- Fingerprint: `{vuln-class}:{plugin-relative-path}#{symbol}`, supplied by the source report and validated using `fingerprinting-spec.md`. Mark missing or partial if the source report lacks a full fingerprint.
- Source severity.
- File path and line range, if provided.
- Component or subsystem.
- Classification: CWE, MITRE ATT&CK, OWASP, rule ID, or similar.
- One-line summary.
- Evidence location in the source report.
- Validation or remediation notes.
- Downstream handoff notes, if provided.

## Correspondence Mapping

Match source findings by:

- Fingerprint overlap (primary key): identical source-supplied fingerprints, or the same `{plugin-relative-path}#{symbol}` with a related `vuln-class`, are strong correlation candidates. A shared `vuln-class` across different symbols can signal a shared root cause rather than the same finding.
- File path overlap: same file, line range, function, route, template, or configuration file.
- Semantic overlap: same weakness described through different vocabulary.
- Component overlap: same subsystem affected by related issues.
- Control overlap: one report describes exploitability while another describes a compensating control or visibility boundary.
- Coverage overlap: lint-task confirms, narrows, or bounds a red-team or blue-team issue.

Do not force a match. If a finding appears in only one source report, place it under Single-Report Findings.

## Exploit Chain Identification

An exploit chain usually connects:

1. A red-team finding showing an exploitable path.
2. A blue-team finding showing missing, weak, or unsafe telemetry on that path.
3. A lint-task finding or coverage signal showing deterministic confirmation, repeated occurrence, or bounded scope.

Example pattern:

```text
R3: SQL injection is exploitable in an unauthenticated endpoint
B2: The raw-query path emits no structured security event
L4: Unsafe query construction is rule-confirmed in the affected unit and two adjacent units
```

Synthesize that as a joint finding. Do not copy the full source evidence; preserve detail by reference.

## Compensating Controls and Coverage Boundaries

Credit controls only when documented in a source report or verified by a narrow spot-check.

Examples:

- Lint-task narrows a weakness to one renderer rather than an entire subsystem.
- Blue-team confirms session ID rotation and sufficient audit emission.
- Red-team observed that global CSRF middleware protects state-changing routes.

Do not silently downgrade or upgrade. Explain severity changes.

## Contradiction Resolution

If reports disagree:

1. Identify the contradiction explicitly.
2. Prefer evidence from the source reports if one clearly resolves the issue.
3. Spot-check cited code only when needed to determine which report is correct.
4. Limit spot-checking to five files unless the dispatcher explicitly authorises deeper review.
5. Document the resolution in the Contradictions Resolved section.

Do not paper over contradictions in joint findings.

## Shared Root Cause Identification

Look for architectural or process causes that explain multiple findings, such as:

- No central authorization middleware.
- Inconsistent input validation strategy.
- No shared secure query abstraction.
- No central audit emission framework.
- Ad-hoc logging schemas.
- Security controls implemented per-route instead of centrally.

A shared root cause should list the source findings it explains and the single higher-leverage remediation that closes or reduces them.

## Prioritisation

Order the action plan as follows:

1. Joint Critical findings.
2. Shared root causes with high leverage.
3. Joint High findings.
4. Single-report Critical and High findings.
5. Medium findings.
6. Low findings.
7. Informational or follow-up items.

Within a severity band, prefer fixes that close multiple findings.
