# Step 1 — Query crash logs from DGrep

> **Parent TSG**: [xinvestigator-process-crash](../xinvestigator-process-crash.md)
> **Maps to**: `_step_1_query_crash_logs()` method

## Purpose

Build and execute a DGrep query against `XHealth` / `XLivesiteLog` to retrieve unhandled exception logs for a crashing XInvestigator worker role.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `process_name` | `str` | TSG input (parsed from ICM title, e.g., `AutoAnalysisWorkerRole`) |
| `tenant_name` | `str` | TSG input (parsed from ICM title, e.g., `AutoAnalysisCSESWestCentralUS`) |
| `incident_time` | `datetime` | TSG input (ICM alert creation time) |

## Outputs

| Field | Type | Description |
|---|---|---|
| `crash_logs` | `DataFrame` | DGrep query results containing exception log entries |
| `dgrep_link` | `str` | Shareable DGrep link for manual inspection |
| `log_count` | `int` | Number of log entries returned |

## Processing Logic

1. **Compute time window** — `incident_time ± 1 hour`.

2. **Build scope conditions:**
   ```python
   scope_conditions = {
       "Role": process_name,
       "Tenant": tenant_name,
   }
   ```

3. **Execute DGrep query:**
   ```python
   from xportal import dgrep
   result = await dgrep.query(
       namespaces="XHealth",
       event_names="XLivesiteLog",
       from_time=from_time,
       to_time=to_time,
       server_query='where it.Any("Unhandled exception:")',
       server_query_type="MQL",
       scope_conditions=scope_conditions,
   )
   crash_logs = result.to_df()
   dgrep_link = result.get_dgrep_link()
   ```

4. **Validate results** — If `log_count == 0`, widen to ±2 hours and retry once. If still empty, flag for manual DGrep investigation.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: dgrep-query (dgrep.query — XHealth/XLivesiteLog with MQL server_query and Role/Tenant scope conditions)
AUTOMATABLE: Yes
MANUAL_FALLBACK: DRI opens DGrep portal, selects Diagnostics PROD endpoint, XHealth namespace, XLivesiteLog event, sets Role and Tenant scoping conditions.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is `XHealth` / `XLivesiteLog` the correct namespace/event for all XI services, or do some services log to different namespaces? |
| 2 | Does the DGrep `Role` scoping condition match the `process_name` directly, or does it need a mapping? |
| 3 | Are there additional DGrep fields beyond the exception text that should be projected? |
