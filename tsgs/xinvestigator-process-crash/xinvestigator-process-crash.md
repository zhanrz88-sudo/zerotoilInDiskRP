# XInvestigator Process Crash

> **Source**: User-provided TSG content (XInvestigator Process Crash TSG)
> **Monitor ID**: "Role Process Crash"
> **Incident Example**: [ICM 743516314](https://portal.microsofticm.com/imp/v5/incidents/details/743516314/summary)

## Purpose

Triage and mitigate incidents where an XInvestigator worker role (e.g., `AutoAnalysisWorkerRole`) crashes frequently — typically 16+ times in 60 minutes. This TSG queries DGrep for crash logs, classifies the error pattern, checks for recent deployments, and routes to the appropriate mitigation path (revert deployment, skip failing smoke test, or escalate to service owner).

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `int` | ICM alert |
| `process_name` | `str` | Parsed from ICM title (e.g., `AutoAnalysisWorkerRole`) |
| `tenant_name` | `str` | Parsed from ICM title (e.g., `AutoAnalysisCSESWestCentralUS`) |
| `incident_time` | `datetime` | ICM alert creation time |

## Outputs

| Field | Type | Description |
|---|---|---|
| `error_classification` | `str` | One of: `smoke_test_failure`, `non_smoke_test_crash`, `no_logs_found` |
| `deployment_found` | `bool` | Whether a recent deployment was found in the last 3 hours |
| `mitigation_action` | `str` | Action taken: `reverted_deployment`, `skipped_smoke_test`, `escalated_to_owner`, `pending_investigation` |
| `root_cause_summary` | `str` | Brief description of identified root cause |

## Steps

### Step 1 — Query crash logs from DGrep

[Step Analysis](steps/step-1-query-crash-logs.md)

Build and execute a DGrep query against `XHealth` / `XLivesiteLog` to retrieve unhandled exception logs.

- Time window: `incident_time ± 1 hour`
- Scope conditions: `Role = <process_name>`, `Tenant = <tenant_name>`
- Server query (MQL): `where it.Any("Unhandled exception:")`

```python
from xportal import dgrep

result = await dgrep.query(
    namespaces="XHealth",
    event_names="XLivesiteLog",
    from_time=from_time,
    to_time=to_time,
    server_query='where it.Any("Unhandled exception:")',
    server_query_type="MQL",
    scope_conditions={"Role": process_name, "Tenant": tenant_name},
)
crash_logs = result.to_df()
dgrep_link = result.get_dgrep_link()
```

If `log_count == 0`, widen to ±2 hours and retry once. If still empty, flag for manual DGrep investigation.

### Step 2 — Analyze error pattern

[Step Analysis](steps/step-2-analyze-error-pattern.md)

Classify the exception from crash logs:

| Pattern | Classification |
|---|---|
| `SmokeTest`, `AASmokeTests`, `ParallelTest` + test name | `smoke_test_failure` |
| `403-Forbidden`, `Unauthorized`, `KustoRequestDeniedException`, `CertificateExpiredException` | `smoke_test_failure` |
| `OutOfMemoryException`, `StackOverflowException`, `NullReferenceException`, `TimeoutException`, `SocketException` | `non_smoke_test_crash` |
| No logs found | `no_logs_found` |

Extract: `failing_test_name` (e.g., `RunKustoAccessProductionTest`), `external_service` (e.g., `https://vmainsight.kusto.windows.net`), `error_code` (e.g., `403-Forbidden`).

### Step 3 — Check for recent deployments

[Step Analysis](steps/step-3-check-deployment.md)

Map `process_name` to the corresponding ADO build pipeline via static mapping (see `_references.md`):

| Process Name (prefix) | Pipeline Definition ID |
|---|---|
| `AutoAnalysis` | 395813 |
| `AutoTsg` | 392091 |
| `XD` | 396535 |
| `XlivesiteCollector` | 396539 |
| `XPortalDataProvider` | 396537 |
| `XJPLTrigger` | 396381 |
| `XPortal` | 396578 |
| `AcisExtension` | 399283 |

Query for deployments in `[incident_time - 3h, incident_time]` via Kusto (`1es`/`AzureDevOps`/`Build`) or ADO REST API.

### Step 4 — Route to mitigation

[Step Analysis](steps/step-4-route-mitigation.md)

Branch by `error_classification` and `deployment_found`:

| Condition | Action |
|---|---|
| Smoke test failure AND recent deployment | **Smoke test mitigation** (see below) |
| Smoke test failure AND no recent deployment | **Escalation** — external service issue |
| Non-smoke-test crash AND recent deployment | **Smoke test mitigation** (revert only) |
| Non-smoke-test crash AND no recent deployment | **Escalation** |

**Smoke test mitigation path:**

1. **Safety check**: If `failing_test_name == "RunServiceBusTest"`, **NEVER skip** — revert deployment only.
2. Code bug (NullRef, StackOverflow) → **Revert deployment** via ADO pipeline; monitor for ~15 min.
3. Auth/permission failure (403, cert expired) → **Skip smoke test** via PR to `SmokeTestSettings` in `Storage-XInfrastructure` repo (ref: [Commit 999f4c7f](https://msazure.visualstudio.com/One/_git/Storage-XInfrastructure/commit/999f4c7f)). Notify external service owner. Create tracking work item.

**Escalation path:**

1. Contact service owner for `process_name` immediately (Teams/phone). Provide: incident ID, error summary, DGrep link, crash timeline.
2. If crashes ongoing and increasing → escalate to Sev-2, create bridge. If stabilized → keep Sev-3, monitor.
3. Gather diagnostics: full stack traces, memory/CPU metrics, recent config changes, dependency health.

### Step 5 — Document and follow up

[Step Analysis](steps/step-5-document-followup.md)

- Record `mitigation_action` and `root_cause_summary` in the ICM incident via `incident.add_description`.
- Create a tracking work item for root cause investigation.
- If the error was a smoke test skip, create a work item to re-enable the test after the external issue is resolved.
- If crashes continue after mitigation, re-route to escalation path.

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: icm-get-incident (icm.get_incident — parse incident title + time; incident.add_description — document findings; incident.update_severity — escalate), dgrep-query (dgrep.query — XHealth/XLivesiteLog crash log search), ado-build-query (kusto.query on 1es/AzureDevOps — check recent builds by pipeline definition)
AUTOMATABLE: Partially (Steps 1-3 fully automatable; Step 4 mitigation requires human approval for deployment revert or smoke test skip PR; Step 5 partially automatable — incident.add_description for documenting findings)
MANUAL_FALLBACK: DRI follows DGrep link manually, checks ADO pipelines in browser, applies mitigation per Scenario A or B
```

## Open Questions

| # | Question |
|---|---|
| 1 | What is the exact monitor threshold for crash count/window (source says "16+ times in 60 minutes" but is this configurable per service)? |
| 2 | How is `process_name` mapped to the correct ADO build pipeline programmatically? The source provides a static table but no API. |
| 3 | ~~Is there a programmatic API to check ADO build pipeline deployment status, or must DRIs check the ADO UI manually?~~ **Resolved**: Yes — two approaches available via `ado-build-query` coding ability: (a) Kusto query against `1es`/`AzureDevOps`/`Build` table filtering by `DefinitionName` and `EtlProcessDate > ago(3h)`, (b) ADO REST API via `ado.get_access_token()` + `_apis/build/builds` or `_apis/release/releases` endpoints. |
| 4 | Where is the XLivesiteDC SmokeTestSettings configuration stored — is it in a git repo (Storage-XInfrastructure) or a Geneva DC config? |
| 5 | Are there additional XI services beyond the 8 listed that could trigger this alert? |
