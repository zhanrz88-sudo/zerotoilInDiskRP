# Step 4 — Route to mitigation

> **Parent TSG**: [xinvestigator-process-crash](../xinvestigator-process-crash.md)
> **Maps to**: `_step_4_route_mitigation()` method

## Purpose

Based on the error classification and deployment status, execute the appropriate mitigation: revert deployment, skip failing smoke test, or escalate for non-deployment crashes.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `error_classification` | `str` | From Step 2 |
| `deployment_found` | `bool` | From Step 3 |
| `failing_test_name` | `str` | From Step 2 |
| `exception_type` | `str` | From Step 2 |
| `external_service` | `str` | From Step 2 |
| `pipeline_url` | `str` | From Step 3 |
| `process_name` | `str` | TSG input |
| `incident_id` | `int` | TSG input |
| `dgrep_link` | `str` | From Step 1 |
| `error_summary` | `str` | From Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `mitigation_action` | `str` | `reverted_deployment`, `skipped_smoke_test`, `escalated_to_owner`, `pending_investigation` |
| `mitigation_details` | `str` | Description of what was done |

## Processing Logic

**Routing decision table:**

| Condition | Action |
|---|---|
| Smoke test failure AND recent deployment | **Smoke test mitigation path** (see below) |
| Smoke test failure AND no recent deployment | **Escalation path** — external service issue |
| Non-smoke-test crash AND recent deployment | **Smoke test mitigation path** (revert only) |
| Non-smoke-test crash AND no recent deployment | **Escalation path** |

### Smoke Test Mitigation Path

1. **Safety check**: If `failing_test_name == "RunServiceBusTest"`, **NEVER skip this test** — route to deployment revert only.

2. **Choose action:**
   - Code bug (NullRef, StackOverflow, logic error) → **Revert deployment**
   - Auth/permission failure (403, cert expired) → **Skip smoke test**
   - `RunServiceBusTest` failure → **Revert deployment** (skip forbidden)
   - Unclear → **Revert deployment** (safer default)

3. **Revert deployment**: Identify deployment from `pipeline_url`, revert to previous stable version, monitor for crash resolution (~15 min). Create work item for root cause fix. Set `mitigation_action = "reverted_deployment"`.

4. **Skip smoke test**: Submit PR to `SmokeTestSettings` in `Storage-XInfrastructure` repo setting `"<failing_test_name>": false`. Reference PR: [Commit 999f4c7f](https://msazure.visualstudio.com/One/_git/Storage-XInfrastructure/commit/999f4c7f). Notify external service owner. Create tracking work item. Set `mitigation_action = "skipped_smoke_test"`.

### Escalation Path

1. Contact service owner for `process_name` immediately (Teams/phone). Provide: incident ID, error summary, DGrep link, crash timeline.
2. If crashes ongoing and increasing → escalate to Sev-2, create bridge.
3. If crashes stabilized → keep Sev-3, monitor.
4. Gather diagnostics: full stack traces, memory/CPU metrics, recent config changes, dependency health.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: icm-get-incident (incident.add_description, incident.update_severity, incident.transfer), ado-build-query (ado.get_item_content for SmokeTestSettings)
AUTOMATABLE: Partially (safety check and decision logic automatable; deployment revert and PR submission require human action; severity update and ICM documentation automatable)
MANUAL_FALLBACK: DRI reverts via ADO pipeline UI or submits PR to Storage-XInfrastructure, contacts service owner manually.
```

## Open Questions

| # | Question |
|---|---|
| 1 | What is the exact file path of `SmokeTestSettings` in `Storage-XInfrastructure`? |
| 2 | Is there a standardized PR template or approval process for smoke test skip PRs? |
| 3 | How long does a smoke test skip PR take to propagate to the affected service? |
| 4 | Are there other critical smoke tests besides `RunServiceBusTest` that should never be skipped? |
| 5 | Is there a definitive mapping from XI `process_name` to the owning team and on-call contact? |
| 6 | What is the exact threshold for Sev-3 → Sev-2 escalation (crash count, duration, impact scope)? |
