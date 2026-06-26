# SRA Rating Model

## Impact ratings

* `Severe`: major exposure or disruption of sensitive systems or data; full site outage; broad compromise; unacceptable CIA impact without controls.
* `Significant`: serious exposure or disruption; likely PII, credentials, privileged access, sensitive tenant data, regulated/compliance-critical records, or important business impact.
* `Moderate`: meaningful but bounded CIA impact; user or tenant security posture reduced; limited sensitive data or functionality affected; inaccurate internal workflow records where impact is constrained and recoverable.
* `Minor`: minimal CIA impact; constrained exposure or disruption; low-consequence records or functionality affected.
* `Minimal`: no meaningful interaction with sensitive systems or data.

Treat highly critical systems, such as login, authentication, authorization, tenant isolation, core platform access, privileged administration, and broad data access, as having higher impact when CIA risk is present.

## Bounded data integrity guidance

For internal workflow records such as attendance, seminar participation, booking status, activity completion, course progress, checklist state, or similar LMS/product functionality:

* Default to `Moderate` impact when compromise is limited to inaccurate internal records, bounded to a course/session/activity/user group, and administratively correctable.
* Use `Minor` when the affected record is primarily informational and has low business consequence.
* Escalate to `Significant` only when the record is confirmed to be used for high-consequence workflows such as compliance evidence, certification, regulated training, safeguarding, payroll, funding, contractual reporting, disciplinary action, legal/audit evidence, customer billing, entitlement decisions, or downstream access control.
* Escalate to `Severe` only when the issue affects core platform security, tenant boundaries, authentication, privileged access, broad sensitive-data exposure, or full-site availability.

Do not rate internal data-integrity issues as `Significant` solely because integrity is affected.

Do not rate internal data-integrity issues as `Significant` solely because high-consequence use is possible. If high-consequence use is not confirmed, use one of:

* `Moderate` impact with an open question about high-consequence use; or
* `Unknown` if the answer materially determines whether the risk is bounded or high-consequence.

Use this pattern:

> Ordinary LMS workflow use: `Moderate` impact by default.
> Confirmed compliance/certification/payroll/legal/regulatory use: consider `Significant`.
> Unknown business consequence: use `Moderate with open questions` or `Unknown`, not speculative `Significant`.

## Likelihood ratings

* `Almost certain`: expected to occur as part of normal operation or common use.
* `Probable`: likely to occur under realistic use or attacker behavior.
* `Possible`: credible scenario with plausible conditions.
* `Unlikely`: not expected due to design or controls, but still plausible.
* `Almost never`: only expected if the feature is incorrectly implemented, a generic implementation bug exists, or standard platform controls are omitted contrary to normal engineering practice.

Use `Almost never` for generic implementation bugs unless there is a concrete design reason, code evidence, observed implementation pattern, known vulnerability, or explicit requirement showing the issue is more likely.

Examples of generic implementation bugs include:

* Missing authentication on a normal web endpoint.
* Missing authorization check where standard platform patterns require one.
* Missing CSRF protection on a state-changing POST handler.
* SQL injection due to failing to use parameterized APIs.
* XSS due to failing to escape user-derived output.
* IDOR caused by missing ownership or relationship validation.
* Missing audit logging where audit logging is a standard release requirement.
* Missing duplicate-prevention where duplicate-prevention is a product correctness requirement.

These may be serious findings if observed in implementation. Sparse prose or feature descriptions should not assume they are likely by default.

Do not rate likelihood as `Probable` merely because a control is not mentioned. Missing control descriptions are open questions unless the design indicates the control is absent or bypassed.

If it is not credible to assert that a generic bug is `Almost never`, and there is insufficient design information to determine likelihood, flag the risk as `Unknown` or request further design work rather than inflating likelihood without a concrete scenario.

## Bespoke vs. standard authorization

`Almost never` applies to absent standard platform controls (require_login, require_capability, require_sesskey, DBAL parameterization) — the platform provides these and omitting them is a generic bug.

Sub-endpoint authorization has no platform analogue and is not standard: per-field save enforcement, pre-condition validation on business-logic gates, per-record scope checks beyond content restrictions. For these, apply:

* Design confirms server-side enforcement → `Almost never`
* Design describes only client-side behavior → `Possible`
* Design is silent → open question with conditional likelihood note

## Client-side control signals

UI language such as "greyed out", "button only visible when X", or "accessible once condition met" indicates a client-side control only. When present: check whether the design also confirms server-side enforcement. If not, register the server-side gap as a distinct risk at `Possible`. A UI control and a server-side control are independent — do not conflate them.

## Authorized actor negligence and collusion

When a risk requires an authorized actor to act within their granted authority — negligently or collusively — the likelihood default is `Unlikely`, not `Possible`. An absent technical constraint does not raise likelihood to `Possible` if exploitation depends on an authorized actor misusing their own legitimate permissions.

Escalate to `Possible` only when the actor can exploit the gap unilaterally without cooperation from another authorized party, or when the design creates a specific structural incentive for misuse.

When a risk requires two authorized actors to cooperate (e.g., requester and approver), treat this as a collusion scenario: `Unlikely` by default.

Do not conflate "policy constraint is absent" with `Possible`. A missing policy ceiling is a governance gap; rate likelihood against the realistic actor model, not against the absence of the constraint.

## Risk matrix

| Impact \ Likelihood | Almost never | Unlikely | Possible | Probable | Almost certain |
| ------------------- | -----------: | -------: | -------: | -------: | -------------: |
| Severe              |       Medium |   Medium |     High | Critical |       Critical |
| Significant         |          Low |   Medium |     High |     High |       Critical |
| Moderate            |          Low |   Medium |   Medium |     High |           High |
| Minor               |     Very Low |      Low |   Medium |   Medium |         Medium |
| Minimal             |     Very Low | Very Low |      Low |      Low |         Medium |

## Qualitative risk definitions

| Security Risk Level | Definition                                                                                                                                                                           | Comment                                                                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Critical            | The feature presents dangerous potential to damage or expose sensitive systems or data.                                                                                              | The feature has unacceptable CIA impact without mitigating controls.                                                                  |
| High                | The feature presents clear potential to disrupt or expose sensitive systems, sensitive data, privileged access, tenant boundaries, or confirmed high-consequence business workflows. | The feature should be evaluated carefully for CIA impact and potential mitigating controls.                                           |
| Medium              | The feature has meaningful but bounded interaction with sensitive systems, data, or business records.                                                                                | The feature has CIA implications, but impact is limited, recoverable, or not clearly high-consequence.                                |
| Low                 | The feature has minimal interaction with sensitive systems or data.                                                                                                                  | The feature has minimal CIA concerns.                                                                                                 |
| Very Low            | The feature does not interact with sensitive systems or data.                                                                                                                        | The feature has no meaningful CIA concerns.                                                                                           |
| Unknown             | The available information is insufficient to make a defensible risk determination.                                                                                                   | Use when missing design or business-context details determine whether the feature is bounded, high-consequence, or security-critical. |

## Unknown risk and missing design details

Use `Unknown` when missing information prevents a defensible assessment.

Prefer `Unknown` over `High` when:

* The feature may be either bounded or high-consequence depending on missing business context.
* The risk depends on design choices that are not described.
* The only path to High risk is an assumed generic implementation bug.
* The assessment cannot distinguish between a normal engineering control requirement and an inherent security risk.
* Open questions determine whether the affected data or workflow has compliance, legal, financial, tenant-boundary, privileged-access, or core-platform impact.

Do not use `High` merely to express uncertainty.

Use `Unknown` or `Medium with open questions` unless a concrete scenario supports both the impact and likelihood ratings.

For LMS attendance, completion, booking, seminar, and course-progress workflows:

* Use `Medium with open questions` when the likely impact is bounded but some implementation details are missing.
* Use `Unknown` when missing business context determines whether the impact is `Moderate` or `Significant`.
* Use `High` only when high-consequence use is confirmed or there is a concrete design/code weakness that supports the rating.

## Control priority versus risk rating

Separate implementation priority from security risk rating.

A control may be `High priority` or required for release even when the feature risk is `Medium`, `Low`, or `Unknown`.

Examples:

* Authentication may be required for release without making every unauthenticated-bug scenario a High inherent risk.
* Authorization checks may be mandatory engineering acceptance criteria even when the affected workflow is bounded.
* CSRF protection may be required by platform standards even when the business impact is moderate.
* Audit logging may be important for supportability and dispute resolution without implying severe security impact.
* Duplicate prevention may be a product correctness requirement rather than a High security risk.
* QR token expiry may be required for a sound implementation without automatically making the feature High risk.
* Access-control tests may be High priority engineering work while the aggregate feature risk remains Medium.

Use priority to express engineering importance.

Use risk rating to express CIA consequence and likelihood.

## Blocking semantics

Distinguish between different kinds of blockers:

* `Blocks final risk rating`: missing information prevents a defensible rating.
* `Blocks production release`: a control or test must be completed before release.
* `Blocks engineering proceeding`: work should not continue until the issue is resolved.

Do not mark an item as `blocks engineering proceeding` merely because it is High priority.

For bounded LMS workflow risks, prefer:

* `blocks final risk rating` for missing business consequence or design details;
* `blocks production release` for required implementation controls;
* `does not block engineering proceeding` when normal engineering review can continue safely.

Example:

> Confirm whether attendance feeds compliance or certification workflows: blocks final risk rating.
> Verify `require_login()`, `require_capability()`, and `require_sesskey()`: blocks production release.
> Conduct full threat model: conditional; required only if high-consequence use or complex trust boundaries are confirmed.

## Aggregate risk

Set aggregate risk to the highest individual risk rating unless there is a clearly justified reason to lower it based on scope, controls, business consequence, or uncertainty.

Include:

* Highest individual risk rating.
* Aggregate risk rating.
* Explanation of why the aggregate rating makes sense.
* Comparison against the qualitative definition for that rating.
* Any proportionality adjustment applied.

## Proportionality override

It is acceptable to set aggregate risk lower than the highest individual risk when the highest-rated risk is narrow, bounded, recoverable, speculative, or conditional.

A lower aggregate rating may be justified when all or most of the following apply:

* The issue is limited to one feature, workflow, course, activity, session, or bounded user group.
* The affected data is not credentials, secrets, privileged access, tenant-wide data, broad PII, or regulated/high-consequence data.
* The issue does not affect authentication, authorization, tenant isolation, core platform access, privileged administration, or broad site availability.
* The impact is administratively recoverable.
* The highest risk depends on an assumed generic implementation bug rather than a known design weakness.
* The feature does not feed compliance, certification, payroll, funding, contractual reporting, legal evidence, disciplinary action, billing, entitlement, or access-control decisions.
* Existing platform controls are expected to apply and no evidence suggests they are bypassed.
* Open questions remain, but the likely business impact is bounded.
* The highest-rated risk is conditional on an unconfirmed business context.

When applying the proportionality override, explain the scope limitation explicitly.

Example:

> Highest individual risk is conditionally High due to possible replay of an attendance token. Aggregate risk is Medium because the impact is bounded to correctable seminar attendance records, does not affect core LMS security or tenant isolation, and is not known to feed compliance, certification, payroll, funding, legal evidence, entitlement, or access-control workflows.

Do not use the proportionality override when the highest individual risk involves:

* Authentication or login.
* Privileged access.
* Tenant isolation.
* Broad sensitive-data exposure.
* Credentials, secrets, or session compromise.
* Core platform availability.
* Payment, payroll, certification, compliance, legal, or regulated workflows.
* Irrecoverable or hard-to-detect integrity compromise.
* Confirmed implementation evidence of a serious vulnerability.

## Conditional escalation

Use conditional escalation when a risk is bounded under ordinary use but materially higher under specific business conditions.

Format conditional ratings like this:

| Scenario                                             |      Impact | Likelihood |  Rating |
| ---------------------------------------------------- | ----------: | ---------: | ------: |
| Ordinary internal workflow use                       |    Moderate |   Possible |  Medium |
| Confirmed compliance/certification/payroll/legal use | Significant |   Possible |    High |
| Missing business context                             |     Unknown |    Unknown | Unknown |

For the primary risk register, use the ordinary or currently evidenced scenario. Record the high-consequence scenario as conditional escalation unless it is confirmed.

Do not use the conditional high-consequence scenario as the default rating.

## Decision guidance

Use aggregate risk, open questions, and proportionality to recommend next steps:

* `Critical`: require security team involvement and threat modelling before proceeding.
* `High`: recommend threat modelling and security team or architect review.
* `Medium`: document the assessment and proceed with normal engineering review unless open questions materially affect impact or likelihood.
* `Low`: document the assessment and proceed with normal engineering review unless open questions remain.
* `Very Low`: document no meaningful CIA concerns and proceed.
* `Unknown`: request further design work before risk can be assessed.

Map to output decisions:

* Use `security_team_required` for Critical risk, confirmed High risk requiring mandatory security intervention, or when security review is explicitly required by policy.
* Use `threat_model_required` when architecture-level abuse cases, trust boundaries, cross-tenant data flows, external integrations, privileged operations, or confirmed high-consequence workflows are the primary concern.
* Use `proceed_with_review` when the feature has bounded CIA impact but still needs normal engineering, architecture, product, security-champion, or code review.
* Use `proceed` when normal engineering review is sufficient and no material open questions remain.
* Use `insufficient_information` when missing information determines whether the feature is bounded, high-consequence, or security-critical.

## Decision calibration

Use `security_team_required` only when:

* aggregate risk is `Critical`;
* High risk is confirmed and requires mandatory security intervention;
* policy explicitly requires security review;
* the feature touches authentication, authorization, privileged access, tenant isolation, broad sensitive data, core platform access, or high-consequence regulated workflows.

Do not use `security_team_required` solely because standard controls need verification.

Use `threat_model_required` when architecture-level abuse cases, trust boundaries, or data flows are the primary uncertainty.

Do not use `threat_model_required` for every bounded workflow feature with missing implementation details.

Use `proceed_with_review` when:

* the feature has bounded CIA impact;
* controls are required before production release;
* normal engineering/security-champion review is sufficient;
* open questions exist but do not automatically imply High risk.

Use `proceed` when normal engineering review is sufficient and no material open questions remain.

Use `insufficient_information` when missing information determines whether the feature is bounded, high-consequence, or security-critical. Use this when uncertainty is the primary blocker.

## Assessment calibration rules

When rating a risk:

1. Identify the affected asset or workflow.
2. Determine whether the asset is core platform security, sensitive data, privileged access, tenant-wide data, or bounded product data.
3. Determine whether the affected workflow is confirmed high-consequence, ordinary internal workflow, or unknown.
4. Rate impact based on consequence, not merely the existence of CIA impact.
5. Rate likelihood based on concrete design facts, known behavior, observed implementation, or realistic attacker behavior.
6. Treat generic implementation bugs as `Almost never` unless evidence supports a higher likelihood.
7. Do not rate likelihood as `Probable` merely because a standard control is not mentioned.
8. Use `Unknown` when missing design or business facts determine the rating.
9. Separate required controls from risk severity.
10. Separate final-rating blockers, production-release blockers, and engineering-proceeding blockers.
11. Apply the proportionality override when the highest individual risk overstates the aggregate feature risk.
12. Explain any escalation or de-escalation clearly.

## LMS workflow examples

### QR attendance plugin

Default rating when attendance is ordinary internal seminar attendance:

* Impact: `Moderate`
* Likelihood: `Possible` for QR sharing/replay if no design detail is available
* Risk: `Medium`
* Decision: `proceed_with_review`
* Notes: require QR validation, expiry, authorization, CSRF, duplicate-prevention, and access-control testing before release.

Conditional escalation:

* Escalate to `High` if attendance is confirmed to feed compliance, certification, payroll, funding, regulated training, safeguarding, legal evidence, entitlement, or access-control decisions.
* Use `Unknown` if the business consequence of attendance cannot be determined and materially affects the rating.

### Missing authorization in sparse prose

Do not rate as `Probable` simply because authorization is not described.

Default:

* Impact: based on affected workflow.
* Likelihood: `Almost never` if this is only a generic implementation bug.
* Rating: matrix-derived, usually `Low` or `Medium`.

Escalate only if:

* design says scanning is unrestricted;
* code shows missing `require_login()` or `require_capability()`;
* endpoint is intentionally public;
* known implementation evidence indicates authorization is likely absent.

### Completion record manipulation

Default rating when completion is ordinary internal LMS progress tracking:

* Impact: `Moderate`
* Likelihood: based on concrete design facts.
* Risk: usually `Medium` or lower.

Escalate to `Significant` only if completion controls certification, compliance, payment, entitlement, regulated evidence, or access to downstream sensitive functionality.
