# Discipline Rules

Use these rules as a final quality gate before returning a consolidated security review.

## Synthesis, Not Summary

A consolidated report that only lists each source report's findings is a failure. The value is cross-referencing, exploit chains, shared root causes, compensating controls, coverage boundaries, and operational handoff quality.

Every Joint Finding must combine evidence from at least two source reports. If a finding only references one source, move it to Single-Report Findings.

## Preserve Detail By Reference

Cite source finding identifiers such as R1, B3, and L2. Do not copy large source-report passages into the consolidation.

The reader should understand the prioritised action and rationale from the consolidated report while still being able to drill down into source reports for full evidence, PoC, and remediation detail.

## Joint Severity Discipline

Joint severity is the outcome across exploitability, code-level visibility, and deterministic coverage confidence.

Do not:

- Average source severities.
- Default to the highest source severity.
- Include operational defence assumptions in joint severity.
- Silently adjust severity without explaining why.

Use `severity-rubric.md`.

## Contradictions Must Be Resolved

If source reports disagree, resolve the contradiction or document it as unresolved.

Do not silently include contradictory claims in the same finding.

Spot-read code only when needed to resolve a contradiction or verify a chain hypothesis. Limit spot-checking to five files unless the dispatcher explicitly authorises deeper review.

## Controls and Boundaries Must Be Credited Correctly

Credit each source for the evidence it can provide:

- Red-team: exploitability, attack preconditions, impact, and controls observed during attack analysis.
- Blue-team: code-level visibility, telemetry quality, sensitive logging or response exposure, and code-level preventive controls.
- Lint-task: deterministic rule confirmation, repetition, isolation, and coverage boundaries.

Do not invent compensating controls.

Do not inflate severity by ignoring controls or narrowing evidence.

## Root Cause Grouping

When multiple findings trace to one architectural or process issue, create a Shared Root Cause entry. A report that lists many findings without grouping common causes has missed remediation leverage.

## File Path Precision

Carry source reports' `file:line` references through consistently. The fixer needs concrete locations.

If a source report lacks file or line references, say so. Do not invent them.

## Fingerprint Every Finding

Every Joint Finding and Single-Report Finding must carry the source-supplied fingerprint in the form `{vuln-class}:{plugin-relative-path}#{symbol}`, validated per `fingerprinting-spec.md`. The fingerprint is the stable identity used for correspondence and re-scan tracking; carry it alongside, not instead of, the source finding ID.

If a source report lacks a fingerprint or provides only a partial fingerprint, record that state and name the unresolved component. Do not fabricate a symbol or path during consolidation to complete a fingerprint.

## No Invented Findings

Do not create new Joint Findings from patterns the source reports did not identify.

If you notice a plausible issue not present in source reports, raise it as a hypothesis or Strategic Recommendation, not as a finding.

## Operational Defence Boundary

Do not assess:

- SIEM rule firing.
- Alert routing.
- Runbook readiness.
- Incident response rehearsal.
- On-call coverage.
- MFA enforcement at the IdP.
- Backup execution.
- Key rotation cadence in production.
- Operational metrics such as MTTD or MTTR.

Aggregate relevant concerns into Operational Defence Handoff for a separate engagement.

## Missing or Shallow Inputs

If a report is missing or shallow, say so in the Executive Summary, Source Report Status table, and What This Consolidation Did Not Cover section.

A partial consolidation is acceptable. An overconfident partial consolidation is not.

## Final Self-Review

Before returning the report, verify:

1. Every Joint Finding combines findings from multiple source reports.
2. At least one exploit chain or shared root cause is identified when the reports contain enough material to support one.
3. Compensating controls and coverage boundaries are credited to the correct source.
4. Contradictions are resolved or explicitly documented as unresolved.
5. The Prioritised Action Plan ranks high-leverage root-cause fixes appropriately.
6. Source finding identifiers are used consistently, and every source finding carries a fingerprint (or a marked partial fingerprint); missing fingerprints are disclosed as source-report defects.
7. Operational Defence Handoff is substantive and tied to actual findings.
8. Out-of-scope domains and missing inputs are explicit.
9. The report does not drift into fresh code review.
