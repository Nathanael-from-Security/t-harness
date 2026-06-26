---
name: security-risk-assessment
description: Produce machine-readable Security Risk Assessment (SRA) JSON for product features, design descriptions, epics, pull requests, architecture proposals, and other changes. Use when assessing security risk, normalizing a design description into structured SRA input, classifying confidentiality/integrity/availability implications, rating impact and likelihood, validating aggregate risk, or deciding whether threat modelling, security team involvement, security champion review, architect review, privacy/legal review, or stakeholder notification is needed.
---

# Security Risk Assessment

## Purpose

Produce a concise Security Risk Assessment (SRA) as a single valid JSON object that supports a risk-based decision about whether further assessment is needed.

The SRA is a triage and decision artifact. Do not perform a full threat model unless the user explicitly asks for one. Focus on scope, CIA classification, risk quantification, aggregate validation, and next steps.

## Required references

Before producing an assessment, read:

- `references/input-format.md` for the preferred `design_description` input structure.
- `references/output-schema.md` for the required JSON output contract.
- `references/rating-model.md` for impact, likelihood, risk matrix, aggregate risk, and decision rules.

Read `references/examples.md` only when an example would help resolve ambiguity.

## Input handling

Accept either a structured `design_description` object or unstructured prose.

When the user provides prose, internally normalize it into the `design_description` structure. Do not invent missing facts. Put missing or unclear facts in `input_completeness.missing_input`, `input_completeness.blocking_gaps`, and `open_questions`.

If the design description is too incomplete for a defensible risk decision, still return valid JSON and set:

- `decision.outcome` to `insufficient_information`
- `aggregate_risk.rating` to `Unknown`
- `recommended_next_steps` to include specific information needed to continue

## Output contract

Return only valid JSON. Do not wrap the JSON in Markdown fences. Do not include prose before or after the JSON object.

Every assessment must include these top-level keys:

```json
{
  "assessment_metadata": {},
  "input_completeness": {},
  "scope": {},
  "cia_classification": {},
  "stakeholders": [],
  "risk_register": [],
  "aggregate_risk": {},
  "decision": {},
  "recommended_next_steps": [],
  "assumptions": [],
  "open_questions": []
}
```

Use empty arrays for absent lists. Use `"unknown"` for unknown strings. Use `false` for unknown booleans unless the field is explicitly true. Keep enum values exactly as defined in `references/output-schema.md`.

## Core workflow

1. Identify the feature or change being assessed.
2. Normalize the available design details into the structured input model.
3. Separate new or changed behavior from unchanged existing functionality.
   - Define `components_in_scope`: only components being added or modified.
   - Define `unchanged_existing_behavior` and `components_out_of_scope`.
   - Use platform knowledge to answer factual questions about unchanged components — do not flag these as missing input.
4. Define scope, out-of-scope areas, assumptions, and affected stakeholders.
5. Resolve missing information before building the risk register:
   - Platform-answerable facts (authorization patterns, job scheduling, tenant isolation, logging): resolve using domain knowledge.
   - Business/product context (high-consequence use, interval constraints, deployment specifics): flag as blocking gaps only if they materially change the risk rating.
   - Design-choice gaps (will a CLI be added?): surface as open questions; do not block the assessment unless the answer determines whether a high-consequence risk exists.
6. Classify confidentiality, integrity, and availability relevance.
7. Build a risk register using concrete actor/action/asset/impact statements.
   - Every risk must reference a component in `components_in_scope`.
   - Do not register risks for `unchanged_existing_behavior` or `components_out_of_scope`.
   - If a concern applies to unchanged behavior, record it as an assumption or open question, not a risk.
8. Rate each risk with the impact and likelihood enums.
9. Derive each risk rating from the risk matrix.
10. Set aggregate risk to the highest individual risk unless a lower aggregate rating is explicitly justified by scope or controls.
11. Choose the decision outcome and required involvement from the decision guidance.

## Risk statement format

Prefer concrete risk statements in this form:

```text
<actor> may <action> affecting <asset>, causing <CIA impact>.
```

Examples:

- An attacker may bypass MFA and access privileged accounts, causing confidentiality and integrity impact.
- A lower-privileged tenant user may modify another tenant's configuration, causing integrity impact.
- An unauthenticated user may exhaust login resources, causing availability impact.

## Security relevance rules

Security risk is composed of confidentiality, integrity, and availability.

- Confidentiality: limiting feature or data access to only those who should have access.
- Integrity: ensuring accuracy of data or information presented.
- Availability: ensuring a feature or data is accessible to those who need it.

Integrity and availability are security-relevant when the issue can be weaponized:

- A server outage is normally a maintenance issue; User A causing a server outage is a security issue.
- User A losing their own data is normally a maintenance issue; User B deleting User A's data is a security issue.

Do not treat unchanged existing functionality as newly introduced risk unless the new feature changes exposure, behavior, trust boundary, or impact.

## Working rules

- Timebox the SRA. Spend a few minutes for small or recurring changes and not more than about 30 minutes for complex or new features unless the user asks for deeper analysis.
- Prefer explicit uncertainty over invented facts.
- Separate product or operational reliability concerns from security concerns unless another user, tenant, attacker, or lower-privileged actor can cause the impact.
- Include privacy and stakeholder impacts when confidentiality involves PII, GDPR, logs, exports, integrations, tenant data, exports, reports, or external data transfer.
- Mark generic implementation bugs as `Almost never` likelihood unless the design creates a specific credible failure mode.
- If generic implementation-bug likelihood cannot defensibly be `Almost never`, flag the design for further work rather than inflating likelihood without a concrete scenario.

## Platform knowledge integration (Totara / Moodle)

When assessing a Totara or Moodle feature, use domain knowledge to answer factual questions about the platform's architecture, controls, and patterns. Do not flag these as missing input or blocking gaps.

**Authorization and access control**
- Standard entry-point guards: `require_login()`, `require_capability()` in the correct context, `require_sesskey()` on state-changing requests.
- Capability checks use context objects resolved from trusted record IDs, not raw user-supplied values.
- Role-based access control is enforced at the database and service layers; capabilities are defined per-feature.

**Multi-tenant isolation**
- Tenant scoping is enforced in database queries via tenant context; the platform's core query layer filters by tenant.
- Cross-tenant data access requires explicit policy grants; absent a grant, tenant boundaries are enforced by default.
- New features inherit tenant scoping from the standard query and context APIs unless they bypass them.

**Scheduling and job execution**
- Moodle's task scheduler runs via cron; tasks are registered as scheduled or ad hoc task classes.
- Concurrency is limited by the number of cron processes configured on the host.
- No application-layer rate limiting exists by default; resource exhaustion from excessive tasks is a valid concern and should be addressed through input validation and job-queue monitoring.

**Audit and event logging**
- Totara uses Moodle's event system; security-relevant events should fire `\core\event\*` subclasses with appropriate context.
- Configuration changes and user actions on sensitive features are expected to emit events; absence is a control gap, not a pre-existing unknown.

**Input validation and output escaping**
- Parameters are validated via `required_param()` / `optional_param()` with `PARAM_*` type constants.
- Output is escaped via `s()`, `format_string()`, `format_text()`, or Mustache template auto-escaping.
- Database queries use placeholders via the DBAL; direct string interpolation is a known anti-pattern.

**Resolving gaps with platform knowledge**

Before marking a fact as missing input, ask: "Can this be answered from Totara/Moodle platform knowledge?"

| Question | Resolution |
|---|---|
| How is authorization enforced for this feature area? | Standard `require_capability()` pattern; assume present unless design or code indicates otherwise |
| How is multi-tenant isolation maintained? | Platform core enforces tenant context in queries; assume applied unless explicitly bypassed |
| What are the resource limits for scheduled tasks? | OS/cron-level; no app-layer rate limit — recommend input validation as a control |
| Is audit logging in place? | Events are expected; note as a required control, not an unknown |
| How are inputs validated? | `PARAM_*` types via `required_param()` / `optional_param()`; assume present unless design indicates absent |

## Scope and risk validation

Before finalizing the risk register, validate every entry against scope.

**Mandatory checks**:
1. Every `risk_register[].component` must appear in `scope.components_in_scope`.
2. No risk may reference a component listed in `scope.components_out_of_scope` or `scope.unchanged_existing_behavior`.
3. Do not fabricate components. If a risk cannot be mapped to an in-scope component, remove the risk or reframe it so it applies to a component that is genuinely in scope.

**Reframing vs. removing**

If a concern relates to how a new in-scope component interacts with an existing system, reframe the risk so the component is the new element:

- Wrong: risk about "multi-tenant isolation" when isolation is listed as unchanged.
- Right: risk about "new CLI interface failing to enforce tenant context" when CLI is in scope.

If the concern applies entirely to unchanged behavior and the new feature does not interact with it, remove the risk and record it as an assumption if relevant.
