# Step 5 — Document and follow up

> **Parent TSG**: [xinvestigator-process-crash](../xinvestigator-process-crash.md)
> **Maps to**: `_step_5_document_followup()` method

## Purpose

Record mitigation results in the ICM incident and create tracking work items for root cause investigation and any deferred actions (e.g., re-enabling a skipped smoke test).

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `int` | TSG input |
| `mitigation_action` | `str` | From Step 4 |
| `root_cause_summary` | `str` | From Step 4 |
| `dgrep_link` | `str` | From Step 1 |
| `error_classification` | `str` | From Step 2 |
| `failing_test_name` | `str` | From Step 2 (if applicable) |

## Outputs

| Field | Type | Description |
|---|---|---|
| `incident_updated` | `bool` | Whether ICM incident was annotated successfully |
| `tracking_work_item` | `str` | Work item ID created for follow-up |

## Processing Logic

1. **Add triage summary to ICM** — Use `incident.add_description` to post mitigation action, root cause summary, DGrep link, and error classification.

2. **Create tracking work item** — For root cause investigation, regardless of mitigation path.

3. **If smoke test was skipped** — Create an additional work item to re-enable the test after the external issue is resolved. Include the external service owner as a reference.

4. **If crashes continue post-mitigation** — Re-route to escalation path (contact service owner, consider Sev-2 bridge).

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: icm-get-incident (incident.add_description — document findings in ICM)
AUTOMATABLE: Partially (ICM updates automatable; work item creation requires ADO API; monitoring requires human follow-up)
MANUAL_FALLBACK: DRI updates ICM incident manually and creates work items in ADO.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is there a standard work item template for XI process crash root cause investigation? |
| 2 | How long should post-mitigation monitoring continue before closing the incident? |
