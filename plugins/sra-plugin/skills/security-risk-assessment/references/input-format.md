# SRA Input Format

## Preferred input

Prefer a single `design_description` object:

```json
{
  "feature_name": "string",
  "summary": "string",
  "business_context": "string",
  "actors": [
    {
      "name": "string",
      "role": "user | admin | service | external_system | attacker | unknown",
      "privilege_level": "string"
    }
  ],
  "data_types": [
    {
      "name": "string",
      "classification": "public | internal | confidential | restricted | pii | credential | secret | unknown",
      "description": "string"
    }
  ],
  "authentication_authorization": {
    "authentication_required": false,
    "authorization_model": "string",
    "capability_checks": []
  },
  "workflow_steps": [
    {
      "name": "string",
      "description": "string",
      "actors": [],
      "components": [],
      "data_used": []
    }
  ],
  "entry_points": [
    {
      "name": "string",
      "type": "ui | api | webhook | scheduled_job | message_queue | file_import | admin_console | cli | unknown",
      "exposed_to": [],
      "authentication_required": false
    }
  ],
  "trust_boundaries": [
    {
      "name": "string",
      "description": "string",
      "crosses_boundary": false
    }
  ],
  "external_integrations": [
    {
      "name": "string",
      "direction": "inbound | outbound | bidirectional | unknown",
      "data_shared": []
    }
  ],
  "data_lifecycle": [
    {
      "data": "string",
      "collected_from": "string",
      "stored_in": [],
      "processed_by": [],
      "shared_with": [],
      "retention_or_deletion": "string"
    }
  ],
  "client_side_components": [
    {
      "name": "string",
      "description": "string",
      "handles_sensitive_data": false,
      "security_relevant_behavior": []
    }
  ],
  "logging_and_monitoring": {
    "security_events_logged": [],
    "sensitive_data_in_logs": "yes | no | unknown",
    "alerts_or_monitoring": [],
    "auditability_notes": "string"
  },
  "components_in_scope": [],
  "components_out_of_scope": [],
  "new_or_changed_behavior": [],
  "unchanged_existing_behavior": [],
  "existing_controls": [],
  "planned_controls": [],
  "deployment_or_operational_context": "string",
  "assumptions": [
    {
      "assertion": "string",
      "rationale": "string"
    }
  ],
  "open_questions": []
}
```

## Normalization rules

- Accept incomplete input and preserve uncertainty in the output.
- Do not add actors, data types, controls, integrations, workflow steps, entry points, client-side components, logging details, or trust boundaries that are not stated or directly implied.
- Use `"unknown"` for missing scalar facts.
- Use `[]` for missing list facts.
- Treat design changes as in scope only when they are new, modified, newly exposed, or materially affected by the proposed change.
- Treat unchanged existing behavior as out of scope. Do not add it to `components_in_scope`. Do not register risks against it.
- Before marking a fact as missing, check whether it can be answered from platform knowledge (see SKILL.md — Platform knowledge integration). Platform-answerable facts are not missing input.

## Gap categorization

Not all missing information is equal. Categorize gaps before populating `input_completeness`:

**Platform-answerable** — resolve using Totara/Moodle domain knowledge; do not list in `missing_input` or `blocking_gaps`.

Examples:
- How authorization is enforced for this feature area.
- How multi-tenant isolation is maintained.
- What input validation patterns the platform uses.
- Whether audit logging is expected and how events are emitted.

**Blocking gaps** — business or product context that materially changes the risk rating; must be resolved before a final risk rating can be given. List in `input_completeness.blocking_gaps`.

Examples:
- Whether affected records feed compliance, certification, payroll, or regulated workflows.
- Business-driven min/max constraints on user-controlled numeric inputs.
- Whether a feature is accessible to unauthenticated users by design.

**Design-choice gaps** — architectural or product decisions not yet made that affect scope but do not necessarily block a bounded assessment. List as `open_questions` with `blocks_assessment: false` unless the answer determines whether a high-consequence risk exists.

Examples:
- Whether a CLI interface will be added.
- Which specific capability will gate access to a new endpoint.
- Whether a new feature will be available to all tenants or a subset.

Only set `input_completeness.confidence` to `low` when blocking gaps exist and cannot be resolved with platform knowledge.

## Minimum useful information

A defensible SRA usually needs:

- Feature or change name.
- Summary of what is changing.
- Components or workflows in scope.
- Workflow steps and externally reachable entry points.
- Actors and privilege levels.
- Data types affected.
- Data lifecycle, especially collection, storage, sharing, retention, and deletion.
- Authentication and authorization behavior.
- Client-side handling of sensitive data, if any.
- External integrations or trust-boundary crossings.
- Security logging, monitoring, and auditability expectations.
- Existing or planned controls.

Many of these can be partially answered from platform knowledge for Totara/Moodle features. Only return `insufficient_information` when blocking gaps remain after applying platform knowledge and the missing context determines whether the feature is bounded or high-consequence.
