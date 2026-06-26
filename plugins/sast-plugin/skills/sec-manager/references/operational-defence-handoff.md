# Operational Defence Handoff Guidance

Use this reference when writing the Operational Defence Handoff section of a consolidated security review.

## Purpose

The source agents assess repository-local evidence only. They cannot determine whether operational defences exist or work unless those defences are represented in repository-resident artifacts.

The handoff converts repository-local findings into next-step questions and inputs for SIEM, detection engineering, incident response, on-call, identity, backup, and platform teams.

## Boundary

Do not claim that any of the following exist, work, fire, route, or are ready unless a source report proves it from repository-resident artifacts:

- SIEM rules.
- Alert routing.
- On-call escalation.
- Incident response runbooks.
- IR rehearsal or tabletop coverage.
- MFA enforcement at the IdP.
- Backup execution or restore testing.
- Production key rotation cadence.
- Operational metrics such as MTTD, MTTR, alert volume, or false positive rate.

## Inputs to Aggregate

Use:

- Blue-team downstream handoff notes.
- Blue-team findings about missing or insufficient event emissions.
- Red-team exploit paths and attack scenarios.
- Lint-task coverage breadth, repetition, and residual gaps.
- Repository-resident detection artifacts if source reports include them.

Do not invent operational facts.

## Detection Capabilities Now Feasible After Remediation

List detections that become feasible once the consolidated remediations are complete.

For each detection candidate, include:

- Scenario or technique.
- Required application event or log source.
- Required fields.
- Basic grouping or threshold concept where appropriate.
- Linked joint findings or source findings.

Example format:

```text
Credential stuffing
- Enabled by: J1 and SRC2 remediation
- Required event: auth.login
- Required fields: event.outcome, user.id or attempted identifier, source.ip, user_agent, correlation_id, failure_reason, timestamp
- Detection concept: group failures by source.ip and attempted identifier over a short window
- Follow-up owner: detection engineering / SOC
```

## Detection Capabilities Still Gapped After Remediation

List scenarios that remain difficult or impossible for the application to distinguish, even after proposed application-level remediation.

Examples:

- Novel exploit payloads where application logs capture the request but cannot classify maliciousness.
- Network-layer attacks requiring WAF, IDS, or reverse-proxy telemetry.
- Host-level execution behavior requiring EDR.
- Identity-provider events outside the repository.

These are not application findings. They are handoff items.

## Operational Concerns For Separate Review

Use this list selectively. Include only items connected to actual findings.

- **SIEM rule existence and firing:** Verify whether detections exist and fire on representative events.
- **Alert routing:** Confirm severity-to-route mapping matches consolidated joint severities.
- **Runbooks:** Create or update runbooks for attack scenarios documented in Joint Findings.
- **IR rehearsal:** Use exploit chains as tabletop candidates.
- **MFA and IdP controls:** Review where findings depend on authentication assurance outside the repo.
- **Backups and restore:** Review only when source findings implicate destructive actions, ransomware paths, or data loss.
- **Key rotation:** Review only when source findings implicate secret exposure or credential compromise.
- **Detection-as-code coverage:** Confirm whether repository-local detection artifacts match the required emissions.

## Handoff Quality Rules

- Tie every operational handoff item to a source finding, joint finding, or shared root cause.
- Separate what becomes feasible after remediation from what remains gapped.
- Do not use generic security-program recommendations unless they are linked to the consolidation.
- Do not assert operational readiness.
- Prefer concrete event names and required fields over vague phrases such as improve monitoring.
