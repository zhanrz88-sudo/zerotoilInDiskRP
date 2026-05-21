# Step 2 — Fetch failure logs

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Maps to**: `_step_2_fetch_failure_logs()`

## Purpose

Collect the recent failed-job rows for this UpgradeAction so the branch in Step 4 has evidence (exception type, message, timestamps) without requiring a human to click into DGrep / blob-explorer.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant` | `str` | Step 1 |
| `operation` | `str` | Step 1 |
| `time_window_hours` | `int` | TSG input (default 6) |

## Outputs

| Field | Type | Description |
|---|---|---|
| `dgrep_rows` | `list[dict]` | Recent log rows: `{ ts, level, exception_type, message, deployment_id }` |
| `dgrep_link` | `str` | Shareable DGrep URL (for ICM discussion) |
| `history_xml_path` | `str` | `xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/<operation>` |
| `history_xml` | `str \| None` | Raw XML body if a blob-read coding ability exists; else `None` |

## Processing Logic

Run the DGrep query based on the context as below:
Namespace: XKulfiTelemetry
EventName: TraceTelemetry

Tenant: XKulfiEastUS-Prod-BL2P (retrieved from dgrep_tenant)
Role: XKulfi

Server Query: where message.contains("Upgrade action SmokeTestOperation for [[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z] result:")
select STG_TenantName, STG_VirtualTenantName, STG_PFEnvironment, message, PreciseTimeStamp, RoleInstance, Tenant
Note message.contains("xxxxx"), where xxxxx is alert_alert_keyword


1. **DGrep query** — use `dgrep-query` to run the DGrep query based on the context as below::
   - Namespace: XKulfiTelemetry
   - EventName: TraceTelemetry
   - Tenant: XKulfiEastUS-Prod-BL2P (retrieved from dgrep_tenant)
   - Role: XKulfi
   - Server Query: where message.contains("Upgrade action SmokeTestOperation for [[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z] result:")
select STG_TenantName, STG_VirtualTenantName, STG_PFEnvironment, message, PreciseTimeStamp, RoleInstance, Tenant
   
   Note message.contains("xxxxx"), where xxxxx is alert_alert_keyword
   Sort descending by timestamp; cap at 50 rows. Extract `exception_type` from the message body when present.
2. **Generate a DGrep share link** (for the ICM evidence package).
3. **History XML (best-effort)** — record the path `xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/<operation>`. If a blob-read coding ability becomes available, fetch and parse; otherwise leave `history_xml=None` and surface the path for human inspection.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - dgrep-query (alert keyword + tenant filter)
  - GAP: no coding ability for reading XML blobs from xdashxstorepublicpf.
    Track as open question; for now, only emit the path string.
AUTOMATABLE: Partially.
  - DGrep portion: Yes.
  - Blob XML portion: No (path is surfaced; human reads it).
MANUAL_FALLBACK: If DGrep returns no rows (keyword filter mismatch),
emit the "Retrieve logs by the alert keyword" link from the incident
itself and the blob path; let Step 4 / Step 5 escalate with that.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Exact DGrep namespace/table used by XKulfi for `XKulfiAutoAlert`? Source TSGs reference the keyword link from the incident page rather than a Kusto-style table name. |
| 2 | Is there a sanctioned read-only API for `xdashxstorepublicpf` blobs that ZeroToil can call (e.g., via XPortal or `xstore.get_account` SAS)? If yes, this step becomes fully automatable. |
| 3 | The history XML schema is not documented in the source TSGs (we only see fragments in step-4i). Need a sample to define the parsed shape. |
