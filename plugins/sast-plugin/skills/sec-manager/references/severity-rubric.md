# Joint Severity Rubric

Use this rubric for consolidated findings that combine evidence from red-team, blue-team, and lint-task reports.

## Severity Axes

Joint severity reflects the combined outcome across three in-scope axes:

1. Exploitability: from the red-team report.
2. Code-level visibility: from the blue-team report.
3. Deterministic coverage confidence: from the lint-task report.

Operational defence is not part of joint severity. SIEM rule firing, alert routing, runbook readiness, incident response rehearsal, MFA enforcement at the IdP, backup execution, key rotation cadence, and operational metrics require a separate engagement.

## Critical

Use Critical when all of the following are true:

- The issue is exploitable on a real attack path.
- The application emits no useful telemetry for that path, or actively leaks sensitive material on the same path.
- Lint-task confirms the weakness on a broad, repeated, or high-value slice of the codebase.

Interpretation:

The attacker can achieve meaningful impact, the application makes the attack hard to detect from application emissions, and deterministic coverage shows the problem is real and not isolated.

Example:

- SQL injection on an unauthenticated endpoint.
- No audit emission for raw-query usage.
- Unsafe query construction appears across multiple database access units in lint-task output.

## High

Use High when any of the following are true:

- The issue is exploitable and there is a major code-level visibility gap.
- The issue is exploitable and lint-task confirms the rule violation in the affected unit.
- The issue is exploitable and emitted telemetry lacks critical context such as source IP, subject, target, outcome, correlation ID, or failure reason.
- Sensitive-field leakage materially worsens an exploitable path.

Example:

- Authenticated SQL injection exists in one execute path.
- The application emits a generic failure event, but the event lacks correlation ID and source IP.
- Lint-task confirms the unsafe-query rule hit in the same path.

## Medium

Use Medium when any of the following are true:

- The issue is exploitable but has meaningful constraints documented by another source report.
- The blue-team gap is moderate rather than severe.
- Lint-task shows the issue is isolated to a narrow unit set rather than systemic.
- Exploitability exists but compensating code-level controls reduce impact or observability risk.

Example:

- Reflected XSS is exploitable in one renderer.
- Blue-team shows partial telemetry for the affected flow.
- Lint-task confirms the rule hit is limited to one template path.

## Low

Use Low when the issue is primarily defence-in-depth on a single axis and the other axes hold strong.

Example:

- A low-value deterministic rule hit exists.
- Red-team could not weaponise it.
- Blue-team already shows sufficient telemetry.
- Lint-task confirms the issue is isolated to one non-critical unit.

## Informational

Use Informational for observations that improve coverage, clarity, or downstream readiness but do not materially change current risk.

Examples:

- Schema enrichment that would improve detection quality.
- Additional audit fields worth adding to existing events.
- Deterministic coverage observations that reduce uncertainty.
- Operational handoff items that require separate assessment.

## Severity Adjustment Rules

Do not average source severities.

Do not automatically choose the highest source severity.

Do not silently adjust severity. If consolidated severity differs from source severity, explain why.

Credit only evidence found in source reports or narrow spot-checks.

Do not include operational defence assumptions in joint severity.

## Source Contribution Boundaries

### Red-team evidence can affect severity by showing

- Exploitability.
- Attack preconditions.
- Impact.
- Existing preventive controls observed during exploitability analysis.

### Blue-team evidence can affect severity by showing

- Missing event emission.
- Insufficient event context.
- Sensitive data exposure through logs or responses.
- Code-level preventive controls.
- Code-level emissions that make residual attacks visible.

### Lint-task evidence can affect severity by showing

- Deterministic confirmation.
- Repetition across units.
- Isolation to a narrow unit set.
- Coverage gaps.
- Rule absence after remediation.

## Operational Defence Boundary

Do not state that alerts exist, fire, route correctly, or have runbooks unless the source reports include repository-resident detection-as-code or runbook artifacts and the claim is scoped to repository content only.

Put operational concerns in the Operational Defence Handoff section.
