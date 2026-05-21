# Step 2 — Check failover completion

> **Parent TSG**: [failover-pending-transaction-primary-stuck-prepare-failover](../failover-pending-transaction-primary-stuck-prepare-failover.md)
> **Maps to**: `_step_2_check_failover_completion()` method

## Purpose

Determine whether the alerted failover already completed, so automation can avoid unnecessary mitigation and close triage safely.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `account_name` | `str` | From Step 1 |
| `incident_start_time_utc` | `datetime` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `is_completed` | `bool` | True when current failover run has a `Complete` status |
| `latest_status` | `str` | Last observed `accountFailoverStatusType` |
| `status_timeline` | `list[str]` | Ordered status sequence in incident window |

## Processing Logic

1. **Query account failover events** — DGrep on `RegionalSRP.AccountFailoverEvent`:
   - Scope: `Tenant == <tenant_name>`
   - Condition: `accountName contains <account_name>`
   - Time: `<incident_start_time_utc - 2h>` to `now()`
   - Server query (MQL): `where accountName.Contains("<account_name>") select PreciseTimeStamp, accountName, accountFailoverStatusType, operationId`

2. **Isolate current failover run** — Sort ascending by `PreciseTimeStamp` and focus on entries at or after incident start to avoid historical runs.

3. **Evaluate completion** — If the selected run contains `accountFailoverStatusType == Complete`, set `is_completed=true`; otherwise `is_completed=false`.

4. **Decision gate**: If `is_completed == true`, the TSG sets `mitigation_status=NoActionNeeded` and **stops** (no further steps needed).

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: dgrep-query (xportal.dgrep.query)
AUTOMATABLE: Yes
MANUAL_FALLBACK: Use DGrep portal to inspect `AccountFailoverEvent` timeline and mark completion state manually.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can `accountFailoverStatusType` transiently emit `Complete` for a prior operation id in the same window, requiring strict operation-id correlation? |
| 2 | Should a timeout threshold be enforced (e.g., no new events for N minutes) before concluding non-completion? |
