# Step 3 — Determine stuck stage and side

> **Parent TSG**: [failover-pending-transaction-primary-stuck-prepare-failover](../failover-pending-transaction-primary-stuck-prepare-failover.md)
> **Maps to**: `_step_3_determine_stuck_stage()` method

## Purpose

Classify where failover is blocked and identify the effective stage by comparing latest Primary and Secondary stage progress from statistics events.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `account_name` | `str` | From Step 1 |
| `incident_start_time_utc` | `datetime` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `stuck_location` | `str` | `Primary`, `Secondary`, or `Unknown` |
| `primary_stage` | `str` | Latest completed stage on primary |
| `secondary_stage` | `str` | Latest completed stage on secondary |
| `effective_stuck_stage` | `str` | Stage inferred as blocked transition point |

## Processing Logic

1. **Query failover statistics events** — DGrep on `RegionalSRP.AccountFailoverStatisticsEvent`:
   - Scope: `Tenant == <tenant_name>`
   - Condition: `accountName contains <account_name>`
   - Time: `<incident_start_time_utc - 2h>` to `now()`
   - Server query (MQL): `where accountName.Contains("<account_name>") select PreciseTimeStamp, accountName, PrimaryStage, SecondaryStage`

2. **Select latest event** — Sort by `PreciseTimeStamp` ascending, take last record as current snapshot.

3. **Determine blocked side** using stage ordering:
   `NotStarted → PrepareFailover → PollFailover → FinalizeFailover → PollFinalizeFailover → DnsSwitch → ShortTermCleanup`
   - If `PrimaryStage` is earlier than `SecondaryStage` → `stuck_location=Primary`
   - If `SecondaryStage` is earlier → `stuck_location=Secondary`
   - If equal or unparsable → `stuck_location=Unknown`

4. **Infer effective stuck stage** — Set to the next expected stage on the slower side. Example: `PrimaryStage=NotStarted` + `SecondaryStage=PrepareFailover` → `effective_stuck_stage=PrepareFailover` on Primary.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: dgrep-query (xportal.dgrep.query)
AUTOMATABLE: Yes
MANUAL_FALLBACK: Manually inspect the last `AccountFailoverStatisticsEvent` row and compare PrimaryStage vs SecondaryStage.
```

## Open Questions

| # | Question |
|---|---|
| 1 | ~~Are there cloud-specific stage values beyond the documented six states that require extending the ordering map?~~ **Resolved**: Yes — `DnsSwitch` is now included in the stage ordering per the updated source TSG. The full ordering is: `NotStarted → PrepareFailover → PollFailover → FinalizeFailover → PollFinalizeFailover → DnsSwitch → ShortTermCleanup`. |
| 2 | When PrimaryStage and SecondaryStage are equal for an extended period, which supplemental signal should determine the true blocker side? |
