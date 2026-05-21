# Step 5 — Update incident and close triage loop

> **Parent TSG**: [failover-pending-transaction-primary-stuck-prepare-failover](../failover-pending-transaction-primary-stuck-prepare-failover.md)
> **Maps to**: `_step_5_update_incident()` method

## Purpose

Add triage evidence and outcome to the incident, and mitigate the incident if appropriate.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `int` | TSG input |
| `mitigation_status` | `str` | From Step 4 (or Step 2 if early exit) |
| `evidence_links` | `list[str]` | DGrep links from prior steps |
| `stuck_stage` | `str` | From Step 3 |
| `is_completed` | `bool` | From Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `incident_updated` | `bool` | Whether incident was annotated |

## Processing Logic

1. Add triage evidence (DGrep links, stage classification, mitigation or escalation action) to the incident discussion via ICM API.
2. **Decision**: Mitigate the incident only if failover is confirmed complete (`is_completed == true`). If transferred or escalated (`mitigation_status == Transferred` or `Escalated`), leave incident open for owning team.
3. If escalated or transferred, leave incident open for the receiving team's ownership.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: icm-get-incident (Incident.add_description, Incident.mitigate)
AUTOMATABLE: Yes
MANUAL_FALLBACK: Manually add triage notes to ICM incident and mitigate through the portal.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Should incident auto-mitigation be blocked when stage is progressing but not yet complete, or is partial progress sufficient for this alert family? |
