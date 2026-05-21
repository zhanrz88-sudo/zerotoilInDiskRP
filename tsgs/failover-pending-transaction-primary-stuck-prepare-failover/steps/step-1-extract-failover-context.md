# Step 1 — Extract failover context from alert

> **Parent TSG**: [failover-pending-transaction-primary-stuck-prepare-failover](../failover-pending-transaction-primary-stuck-prepare-failover.md)
> **Maps to**: `_step_1_extract_failover_context()` method

## Purpose

Find the failover operation context for a pending-transaction alert by querying SRP background activity logs and extracting the operation id and account identifier relevant to the incident window.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `incident_start_time_utc` | `datetime` | TSG input |
| `incident_id` | `int` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `operation_id` | `str` | Operation id extracted from pending failover alert log |
| `account_name` | `str` | Account identified from failover payload or nearby events |
| `dgrep_link` | `str` | Shareable link to evidence query |

## Processing Logic

1. **Query pending failover alert events** — DGrep on `RegionalSRP.ServiceBackgroundActivityEvent`:
   - Scope: `Tenant == <tenant_name>`
   - Time: `<incident_start_time_utc - 2h>` to `<incident_start_time_utc + 30m>`
   - Server query (MQL): `where it.any("LogPendingFailoverTransactionAlertEvent") select PreciseTimeStamp, Message, ActivityId`

2. **Parse operation id from message** — Extract `OperationId` from message pattern: `[AccountFailover] [PendingFailoverOperation] [OperationId: <GUID>, ...]`. If multiple results, choose closest to incident start time.

3. **Resolve account name** — DGrep on `RegionalSRP.AccountFailoverStatisticsEvent` using extracted `operation_id`; retrieve `accountName` from earliest matching record.

4. **Return** `operation_id`, `account_name`, and DGrep share link.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: dgrep-query (xportal.dgrep.query, DGrepQueryResult.get_dgrep_link)
AUTOMATABLE: Yes
MANUAL_FALLBACK: Use DGrep links from ICM and manually copy operation id/account name into triage notes.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Does `AccountFailoverStatisticsEvent` always include `operationId` as a filterable field in all clouds, or should fallback parsing be based on ActivityId correlation? |
| 2 | Is there a stable schema field for account name in `ServiceBackgroundActivityEvent`, or is message parsing always required? |
