# SRA JSON Output Schema

Return exactly one JSON object. Do not include Markdown fences or explanatory prose outside the JSON.

## Required top-level shape

```json
{
  "assessment_metadata": {
    "feature_name": "string",
    "assessor": "string",
    "assessment_date": "YYYY-MM-DD or unknown",
    "participants": [],
    "source_type": "design_description | prose | mixed | unknown"
  },
  "input_completeness": {
    "confidence": "low | medium | high",
    "missing_input": [],
    "blocking_gaps": [],
    "normalization_notes": []
  },
  "scope": {
    "summary": "string",
    "components_in_scope": [],
    "components_out_of_scope": [],
    "new_or_changed_behavior": [],
    "unchanged_existing_behavior": [],
    "scope_rationale": "string"
  },
  "cia_classification": {
    "confidentiality": {
      "applies": false,
      "summary": "string",
      "assets_or_data": [],
      "security_relevance": "string"
    },
    "integrity": {
      "applies": false,
      "summary": "string",
      "assets_or_data": [],
      "security_relevance": "string"
    },
    "availability": {
      "applies": false,
      "summary": "string",
      "assets_or_data": [],
      "security_relevance": "string"
    }
  },
  "stakeholders": [
    {
      "name": "string",
      "type": "users | tenants | admins | product | operations | support | privacy_legal | security | external_party | unknown",
      "reason": "string"
    }
  ],
  "risk_register": [
    {
      "id": "R-001",
      "component": "string",
      "cia": ["confidentiality"],
      "actor": "string",
      "asset": "string",
      "risk_statement": "string",
      "impact": "Minimal | Minor | Moderate | Significant | Severe",
      "likelihood": "Almost never | Unlikely | Possible | Probable | Almost certain",
      "risk_rating": "Very Low | Low | Medium | High | Critical",
      "rationale": "string",
      "existing_controls": [],
      "recommended_controls": [],
      "open_questions": []
    }
  ],
  "aggregate_risk": {
    "highest_individual_risk": "Unknown | Very Low | Low | Medium | High | Critical",
    "rating": "Unknown | Very Low | Low | Medium | High | Critical",
    "is_lower_than_highest": false,
    "lowering_justification": "string",
    "definition_comparison": "string"
  },
  "decision": {
    "outcome": "proceed | proceed_with_review | threat_model_required | security_team_required | insufficient_information",
    "required_involvement": [
      "no_further_security_action"
    ],
    "rationale": "string"
  },
  "recommended_next_steps": [
    {
      "owner": "engineering | security_champion | security_team | architect | product_owner | privacy_legal | operations | unknown",
      "action": "string",
      "priority": "low | medium | high",
      "blocks_proceeding": false
    }
  ],
  "assumptions": [
    {
      "id": "A-001",
      "assertion": "string",
      "rationale": "string",
      "affects_risk": false
    }
  ],
  "open_questions": [
    {
      "id": "Q-001",
      "question": "string",
      "why_it_matters": "string",
      "blocks_assessment": false
    }
  ]
}
```

## Enum rules

Use these exact enum values.

`assessment_metadata.source_type`:

- `design_description`
- `prose`
- `mixed`
- `unknown`

`input_completeness.confidence`:

- `low`
- `medium`
- `high`

`stakeholders[].type`:

- `users`
- `tenants`
- `admins`
- `product`
- `operations`
- `support`
- `privacy_legal`
- `security`
- `external_party`
- `unknown`

`risk_register[].cia`:

- `confidentiality`
- `integrity`
- `availability`

`risk_register[].impact`:

- `Minimal`
- `Minor`
- `Moderate`
- `Significant`
- `Severe`

`risk_register[].likelihood`:

- `Almost never`
- `Unlikely`
- `Possible`
- `Probable`
- `Almost certain`

`risk_register[].risk_rating`, `aggregate_risk.highest_individual_risk`, and `aggregate_risk.rating`:

- `Unknown`
- `Very Low`
- `Low`
- `Medium`
- `High`
- `Critical`

Use `Unknown` only for aggregate fields when the design is too incomplete to assess. Do not use `Unknown` for individual risk ratings; omit speculative risks instead or create open questions.

`decision.outcome`:

- `proceed`
- `proceed_with_review`
- `threat_model_required`
- `security_team_required`
- `insufficient_information`

`decision.required_involvement`:

- `no_further_security_action`
- `informal_security_champion_review`
- `security_team_involvement`
- `architect_or_product_owner_input`
- `legal_privacy_or_stakeholder_input`
- `threat_modelling`
- `further_design_work`

`recommended_next_steps[].owner`:

- `engineering`
- `security_champion`
- `security_team`
- `architect`
- `product_owner`
- `privacy_legal`
- `operations`
- `unknown`

`recommended_next_steps[].priority`:

- `low`
- `medium`
- `high`

## Consistency rules

- Every `risk_register[].risk_rating` must match the risk matrix.
- `aggregate_risk.highest_individual_risk` must equal the highest rating in `risk_register`, unless `risk_register` is empty.
- If `risk_register` is empty and the design is assessable, use `Very Low` aggregate risk.
- If `aggregate_risk.rating` is lower than `aggregate_risk.highest_individual_risk`, set `is_lower_than_highest` to `true` and provide a concrete `lowering_justification`.
- If `decision.outcome` is `insufficient_information`, include at least one `blocking_gaps` item or one `open_questions` item with `blocks_assessment: true`.
- If any confidentiality item involves PII, credentials, secrets, tenant data, reports, exports, logs, or external sharing, include privacy/legal or stakeholder consideration unless there is a rationale not to.
