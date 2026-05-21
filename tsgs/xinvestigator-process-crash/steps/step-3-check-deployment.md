# Step 3 — Check for recent deployments

> **Parent TSG**: [xinvestigator-process-crash](../xinvestigator-process-crash.md)
> **Maps to**: `_step_3_check_deployment()` method

## Purpose

Determine whether a deployment occurred in the last 3 hours for the crashing XI service. Most process crashes occur during or immediately after deployments.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `process_name` | `str` | TSG input |
| `incident_time` | `datetime` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `deployment_found` | `bool` | Whether a deployment was found in the last 3 hours |
| `pipeline_name` | `str` | Service's build pipeline name |
| `pipeline_url` | `str` | URL to ADO build pipeline |
| `last_deployment_time` | `datetime` | Most recent deployment timestamp (if found) |

## Processing Logic

1. **Map process name to pipeline** — Static mapping from `_references.md`:

| Process Name (prefix) | Service | Pipeline Definition ID |
|---|---|---|
| `AutoAnalysis` | AutoAnalysis | 395813 |
| `AutoTsg` | AutoTsg | 392091 |
| `XD` | XD | 396535 |
| `XlivesiteCollector` | XlivesiteCollector | 396539 |
| `XPortalDataProvider` | XPortal DataProvider | 396537 |
| `XJPLTrigger` | XJPL Trigger | 396381 |
| `XPortal` | XPortal | 396578 |
| `AcisExtension` | ACIS Extension | 399283 |

   If no match, set `pipeline_name = "Unknown"` and flag for manual check.

2. **Check pipeline for recent runs** — Query for deployments in `[incident_time - 3h, incident_time]` via Kusto (`1es`/`AzureDevOps`/`Build`) or ADO REST API.

3. **Record result** — `deployment_found`, `last_deployment_time`, `pipeline_url`.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: ado-build-query (kusto.query on 1es/AzureDevOps/Build — query by DefinitionName + time window; ado.get_access_token + REST for release status)
AUTOMATABLE: Yes
MANUAL_FALLBACK: DRI opens ADO build pipeline URL from _references.md, checks build history.
```

## Open Questions

| # | Question |
|---|---|
| 1 | ~~Is there a programmatic API to query recent build pipeline runs?~~ **Resolved**: Yes — `ado-build-query` coding ability provides Kusto and REST approaches. |
| 2 | Is the process-name-to-pipeline mapping always a prefix match, or are there exceptions? |
| 3 | Should we also check for in-progress deployments that haven't completed yet? |
| 4 | Are there additional deployment mechanisms beyond ADO pipelines that could cause crashes? |
