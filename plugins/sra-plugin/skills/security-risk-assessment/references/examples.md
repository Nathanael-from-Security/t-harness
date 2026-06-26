# SRA Examples

## Example input

```json
{
  "design_description": {
    "feature_name": "Hardware-token MFA",
    "summary": "Add hardware-token registration and login verification for privileged users.",
    "business_context": "Improve account takeover resistance for administrators.",
    "actors": [
      {
        "name": "Administrator",
        "role": "admin",
        "privilege_level": "privileged"
      },
      {
        "name": "Attacker",
        "role": "attacker",
        "privilege_level": "unauthenticated or compromised-password"
      }
    ],
    "data_types": [
      {
        "name": "MFA token registration data",
        "classification": "credential",
        "description": "Token identity and registration metadata."
      }
    ],
    "authentication_authorization": {
      "authentication_required": true,
      "authorization_model": "Privileged users can register and manage their own token; admins can enforce policy.",
      "capability_checks": ["mfa_token_register", "mfa_policy_manage"]
    },
    "workflow_steps": [
      {
        "name": "Register hardware token",
        "description": "A privileged user enrolls a hardware token for future MFA challenges.",
        "actors": ["Administrator"],
        "components": ["token registration"],
        "data_used": ["MFA token registration data"]
      },
      {
        "name": "Verify token during login",
        "description": "A privileged user completes a hardware-token challenge after password authentication.",
        "actors": ["Administrator"],
        "components": ["token verification"],
        "data_used": ["MFA token registration data"]
      }
    ],
    "entry_points": [
      {
        "name": "MFA token registration page",
        "type": "ui",
        "exposed_to": ["privileged users"],
        "authentication_required": true
      },
      {
        "name": "MFA verification endpoint",
        "type": "api",
        "exposed_to": ["users completing login"],
        "authentication_required": true
      }
    ],
    "trust_boundaries": [],
    "external_integrations": [],
    "data_lifecycle": [
      {
        "data": "MFA token registration data",
        "collected_from": "Administrator during token enrollment",
        "stored_in": ["application database"],
        "processed_by": ["token registration", "token verification"],
        "shared_with": [],
        "retention_or_deletion": "unknown"
      }
    ],
    "client_side_components": [
      {
        "name": "MFA registration UI",
        "description": "Browser interface used to enroll a hardware token.",
        "handles_sensitive_data": true,
        "security_relevant_behavior": ["initiates token enrollment", "shows registration state"]
      }
    ],
    "logging_and_monitoring": {
      "security_events_logged": ["token registration", "token verification failure"],
      "sensitive_data_in_logs": "unknown",
      "alerts_or_monitoring": [],
      "auditability_notes": "Administrative token policy changes should be auditable."
    },
    "components_in_scope": ["token registration", "token verification", "administrative token policy"],
    "components_out_of_scope": ["password authentication"],
    "new_or_changed_behavior": ["hardware-token challenge during login", "token registration workflow"],
    "unchanged_existing_behavior": ["password authentication"],
    "existing_controls": ["password authentication", "admin capability checks"],
    "planned_controls": ["rate limiting", "audit logging"],
    "deployment_or_operational_context": "Used on the core login path.",
    "assumptions": [
      {
        "assertion": "Password authentication remains unchanged.",
        "rationale": "The design only introduces the second-factor flow."
      }
    ],
    "open_questions": []
  }
}
```

## Example output

```json
{
  "assessment_metadata": {
    "feature_name": "Hardware-token MFA",
    "assessor": "unknown",
    "assessment_date": "unknown",
    "participants": [],
    "source_type": "design_description"
  },
  "input_completeness": {
    "confidence": "medium",
    "missing_input": ["Detailed recovery flow for lost hardware tokens."],
    "blocking_gaps": [],
    "normalization_notes": []
  },
  "scope": {
    "summary": "Assessment covers hardware-token registration, token verification, and administrative token policy for privileged users.",
    "components_in_scope": ["token registration", "token verification", "administrative token policy"],
    "components_out_of_scope": ["password authentication"],
    "new_or_changed_behavior": ["hardware-token challenge during login", "token registration workflow"],
    "unchanged_existing_behavior": ["password authentication"],
    "scope_rationale": "Password authentication is unchanged; the new second-factor flow affects login security and availability."
  },
  "cia_classification": {
    "confidentiality": {
      "applies": true,
      "summary": "MFA bypass could expose privileged accounts and tenant data.",
      "assets_or_data": ["privileged accounts", "tenant data", "MFA token registration data"],
      "security_relevance": "The feature protects access to sensitive accounts and credential-like token data."
    },
    "integrity": {
      "applies": true,
      "summary": "Unauthorized token or policy changes could alter account security state.",
      "assets_or_data": ["MFA token registration data", "MFA policy"],
      "security_relevance": "Attackers or lower-privileged users modifying MFA settings could weaken controls."
    },
    "availability": {
      "applies": true,
      "summary": "Failures or resource exhaustion in the MFA path could block login.",
      "assets_or_data": ["core login path"],
      "security_relevance": "A user-triggered disruption of the login path can become a security availability issue."
    }
  },
  "stakeholders": [
    {
      "name": "Administrators",
      "type": "admins",
      "reason": "Administrators must enroll and use hardware tokens."
    },
    {
      "name": "Security team",
      "type": "security",
      "reason": "The feature changes authentication controls for privileged access."
    }
  ],
  "risk_register": [
    {
      "id": "R-001",
      "component": "token verification",
      "cia": ["confidentiality", "integrity"],
      "actor": "attacker with compromised password",
      "asset": "privileged account",
      "risk_statement": "An attacker with a compromised password may bypass MFA and access a privileged account, causing confidentiality and integrity impact.",
      "impact": "Moderate",
      "likelihood": "Unlikely",
      "risk_rating": "Medium",
      "rationale": "The attacker must already compromise the password, and token verification is intended to block second-factor bypass.",
      "existing_controls": ["password authentication"],
      "recommended_controls": ["confirm capability checks", "add tests for bypass conditions"],
      "open_questions": []
    },
    {
      "id": "R-002",
      "component": "token verification",
      "cia": ["availability"],
      "actor": "unauthenticated attacker",
      "asset": "core login path",
      "risk_statement": "An unauthenticated attacker may exhaust MFA verification resources affecting the core login path, causing availability impact.",
      "impact": "Severe",
      "likelihood": "Possible",
      "risk_rating": "High",
      "rationale": "The MFA path is part of login, and disruption could prevent access to a sensitive core platform function.",
      "existing_controls": [],
      "recommended_controls": ["rate limit verification attempts", "confirm recovery and fail-safe behavior"],
      "open_questions": ["What throttling applies before and during MFA verification?"]
    }
  ],
  "aggregate_risk": {
    "highest_individual_risk": "High",
    "rating": "High",
    "is_lower_than_highest": false,
    "lowering_justification": "",
    "definition_comparison": "High is appropriate because the feature has potential to disrupt a sensitive authentication path and should be evaluated for mitigating controls."
  },
  "decision": {
    "outcome": "threat_model_required",
    "required_involvement": ["security_team_involvement", "architect_or_product_owner_input", "threat_modelling"],
    "rationale": "Authentication and login availability risks require deeper review before proceeding."
  },
  "recommended_next_steps": [
    {
      "owner": "security_team",
      "action": "Threat model MFA registration, verification, recovery, and administrative policy flows.",
      "priority": "high",
      "blocks_proceeding": true
    }
  ],
  "assumptions": [
    {
      "id": "A-001",
      "assertion": "Password authentication remains unchanged.",
      "rationale": "The design only introduces the second-factor flow.",
      "affects_risk": true
    }
  ],
  "open_questions": [
    {
      "id": "Q-001",
      "question": "What throttling applies before and during MFA verification?",
      "why_it_matters": "It determines whether the login availability risk is adequately controlled.",
      "blocks_assessment": false
    }
  ]
}
```
