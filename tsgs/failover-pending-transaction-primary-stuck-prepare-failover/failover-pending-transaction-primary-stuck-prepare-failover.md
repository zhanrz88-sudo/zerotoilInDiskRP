# FailoverPendingTransaction - PrimaryStuck.PrepareFailover

> **Source**: [[FailoverPendingTransaction] Failover for accounts stuck on PrimaryStuck.PrepareFailover in XXX](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/%5BFailoverPendingTransaction%5D%20Failover%20for%20accounts%20stuck%20on%20PrimaryStuck.PrepareFailover%20in%20XXX.md&_a=preview)
> **Related**: [TSG: Failover Pending Transaction Taking Longer to Complete](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/srpdocs/failover/FailoverPendingTransaction-alert.md&_a=preview)

## Purpose

Triage and mitigate incidents where an account failover transaction is pending and appears stuck around `PrimaryStuck.PrepareFailover`. This TSG extracts alert context, determines whether failover already completed, classifies the stuck stage, applies known mitigation when applicable, and escalates when the pattern is unknown.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `int` | ICM alert payload |
| `tenant_name` | `str` | ICM title (e.g., `RSRPWestEurope`) |
| `incident_start_time_utc` | `datetime` | ICM monitor timestamp |
| `environment` | `str` | `Public`, `USSec`, or `USNat` |

## Outputs

| Field | Type | Description |
|---|---|---|
| `account_name` | `str` | Unversioned account identified from failover logs |
| `operation_id` | `str` | Pending failover operation id from alert logs |
| `is_completed` | `bool` | Whether failover already completed |
| `stuck_location` | `str` | `Primary`, `Secondary`, or `Unknown` |
| `stuck_stage` | `str` | Stage inferred from latest statistics event |
| `mitigation_status` | `str` | `Transferred`, `Escalated`, or `NoActionNeeded` |

## Steps

### Step 1 — Extract failover context from alert

[Step Analysis](steps/step-1-extract-failover-context.md)

Query DGrep against `RegionalSRP.ServiceBackgroundActivityEvent` to find the pending failover operation context.

**DGrep Query:**

- Namespace: `RegionalSRP`, Event: `ServiceBackgroundActivityEvent`
- Scope: `Tenant == <tenant_name>`
- Time: `<incident_start_time_utc - 2h>` to `<incident_start_time_utc + 30m>`
- Server query (MQL):

```text
where it.any("LogPendingFailoverTransactionAlertEvent")
select PreciseTimeStamp, Message, ActivityId
```

**Parse operation id** from message pattern: `[AccountFailover] [PendingFailoverOperation] [OperationId: <GUID>, ...]`. If multiple results, choose closest to incident start time.

When the incident title includes an explicit stuck signature (for example `SecondaryStuck.SoftFinalizeFailover`), correlate alert rows by `ActivityId` and prioritize only operation/account candidates whose metric row contains the same stuck signature (`dimensionValues`).

**Resolve account name** by querying `RegionalSRP.AccountFailoverStatisticsEvent` with the extracted `operation_id`; retrieve `accountName` from earliest matching record.

If multiple candidates remain after filtering, sample multiple accounts (recommended: up to 3 unique `operation_id + account_name` pairs) and run Steps 2-4 for each sampled account. This improves diagnosis quality when one account has sparse or missing downstream evidence.

**Produces:** `operation_id`, `account_name`, DGrep evidence link.

### Step 2 — Check failover completion

[Step Analysis](steps/step-2-check-failover-completion.md)

Determine whether the alerted failover already completed to avoid unnecessary mitigation.

**DGrep Query:**

- Namespace: `RegionalSRP`, Event: `AccountFailoverEvent`
- Scope: `Tenant == <tenant_name>`
- Condition: `accountName contains <account_name>`
- Time: `<incident_start_time_utc - 2h>` to `now()`
- Server query (MQL):

```text
where accountName.Contains("<account_name>")
select PreciseTimeStamp, accountName, accountFailoverStatusType, operationId
```

Sort ascending by `PreciseTimeStamp`. Focus on entries at or after incident start to avoid historical runs.

**Decision:** If `accountFailoverStatusType == Complete`, set `is_completed=true`, `mitigation_status=NoActionNeeded`, and **stop**. Otherwise continue.

### Step 3 — Determine stuck stage and side

[Step Analysis](steps/step-3-determine-stuck-stage.md)

Classify where the transaction is blocked and at which stage.

**DGrep Query:**

- Namespace: `RegionalSRP`, Event: `AccountFailoverStatisticsEvent`
- Scope: `Tenant == <tenant_name>`
- Condition: `accountName contains <account_name>`
- Time: `<incident_start_time_utc - 2h>` to `now()`
- Server query (MQL):

```text
where accountName.Contains("<account_name>")
select PreciseTimeStamp, accountName, PrimaryStage, SecondaryStage
```

Select the last record as current stage snapshot. Use stage ordering:

`NotStarted → PrepareFailover → PollFailover → FinalizeFailover → PollFinalizeFailover → DnsSwitch → ShortTermCleanup`

- If `PrimaryStage` is earlier than `SecondaryStage` → `stuck_location=Primary`
- If `SecondaryStage` is earlier → `stuck_location=Secondary`
- If equal or unparsable → `stuck_location=Unknown`

Set `effective_stuck_stage` to the next expected stage on the slower side.

### Step 4 — Diagnose known issues and mitigate or escalate

[Step Analysis](steps/step-4-mitigate-or-escalate.md)

Route to the appropriate diagnostic and mitigation path based on stuck stage and location. Search XDS logs to classify the root cause, then transfer to the owning team or escalate.

**Known-issue matrix:**

| Primary Stage / Secondary Stage | Where to Investigate | Diagnostic Steps | Mitigation |
|---|---|---|---|
| p=PrepareFailover, s=NotStarted **OR** p=NotStarted, s=PrepareFailover | Go to the tenant with the **NotStarted** side (i.e., if s=NotStarted → secondary tenant; if p=NotStarted → primary tenant) | 1. Search account name in **XACServer** (Role) verbose log via XDS Logs on the NotStarted-side tenant<br>2. Check if quarantine cannot finish<br>3. Search account name in **TableMaster** (Role) error log via XDS Logs on same tenant | 1. If TableMaster log shows "cannot split due to LLAM" (e.g., `ERROR: XTableMaster.exe [LB:Split][Msg:Cannot split partition][Reason:Incompatible LLAM Stage]...[LLAMStage:LLAM_COMPLETE_PARTITION_HANDOFF_INTRA_CLUSTER]`), **transfer ICM to Xstore/StorageCRM**<br>2. If TableMaster log shows cannot split for other reasons, **transfer ICM to Xstore/TableMaster** |
| p=PrepareFailover, s=PrepareFailover | Go to **Primary** tenant | 1. Search account name in **Nephos.Account** (Role) perf log via XDS Logs on Primary<br>2. Find multiple `PollFailover` calls<br>3. Pick one call, follow its `ActivityId` to full log<br>4. Check for `GeoConfigOffCounter=x` with `x > 0` | 1. If `GeoConfigOffCounter > 0`, **RA XGeo DRI (Redmond working hours) / `ximi@microsoft.com` (China working hours)** via ICM |
| p=FinalizeFailover, s=FinalizeFailover | Go to **Secondary** tenant | 1. Get XFiles partition state via PowerShell: `$p=Get-XdsPartition -Tenant <secondary> -Table XFiles -Account <versioned account name>`<br>2. Check if any XFile partition is in `GeoReplay:LiveReplay` state | 1. Known issue: XFile replayer gets blocked after finalize.<br>2. **Transfer ICM to XStore/SMB** |
| p=DnsSwitch, s=DnsSwitch | Go to **Secondary** tenant | 1. Search `0x830a382d` in **XACServer** verbose log via XDS Logs on Secondary<br>2. Expected pattern: `INFO: XACServer.exe [ACU][Failover][ORS] ExecuteJob: Failed to refresh containers lock for source account during failoveracuOp=InvalidAcuOp, accountName=<account name>, hr=0x830a382d` | 1. **RA XGeo DRI (Redmond working hours) / `ximi@microsoft.com` (China working hours)** via ICM |

**Default escalation** (not matched above): **RA XGeo DRI (Redmond working hours) / `ximi@microsoft.com` (China working hours)** via ICM.

### Step 5 — Update incident and close triage loop

[Step Analysis](steps/step-5-update-incident.md)

Add triage evidence (DGrep links, stage classification, mitigation or escalation action) to the incident discussion via ICM API. Mitigate the incident only if failover is confirmed complete or known mitigation succeeded.

## Incident Input Extraction

Entry-level TSG — all input parameters beyond `incident_id` are extracted from the ICM incident at runtime inside `_extract_input_from_incident()`.

### Extraction strategy: Regex

The fields appear in a predictable format in the incident title, so simple regex extraction is sufficient. LLM extraction is not needed.

### Field extraction rules

| Field | Source | Rule |
|---|---|---|
| `tenant_name` | ICM title | Regex: `\bin\s+(RSRP\S+)` — capture the RSRP tenant name after "in" |
| `incident_start_time_utc` | `incident.CreateDate` | Direct field read — the ICM monitor's creation timestamp |
| `environment` | ICM title | Regex: `\b(USSec\|USNat)\b` — defaults to `"Public"` when absent |

### Example incident titles

These examples show where each field appears in real incident titles:

```text
Example 1:
  Title: "[FailoverPendingTransaction] Failover pending for account stuck on PrimaryStuck.PrepareFailover in RSRPWestEurope"
  → tenant_name = "RSRPWestEurope"
  → environment = "Public" (no sovereign keyword)

Example 2:
  Title: "[FailoverPendingTransaction] PrimaryStuck.PrepareFailover in RSRPEastUS2"
  → tenant_name = "RSRPEastUS2"
  → environment = "Public"

Example 3:
  Title: "[FailoverPendingTransaction] PrimaryStuck.PrepareFailover in RSRPUSSec01 (USSec)"
  → tenant_name = "RSRPUSSec01"
  → environment = "USSec"
```

### Fallback

If the title does not match, scan incident description entries for the same `RSRP\S+` pattern. If still not found, raise `ValueError` and halt — manual input is required.

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: dgrep-query (xportal.dgrep.query, DGrepQueryResult.get_dgrep_link), icm-get-incident (xportal.icm.get_incident, Incident.add_description, Incident.mitigate, Incident.transfer), xds-api-call (xstore.xds.search_log for XACServer verbose, TableMaster error, Nephos.Account perf; xds.search_by_activity_id for activity tracing; xds.generate_log_search_link for evidence), xds-partition-state (Get-XdsPartition for XFiles partition state — coding ability NOT yet available)
TSG_CALL: None
AUTOMATABLE: Partially (Steps 1-3 fully automatable; Step 4 Branches A/B XDS log search and pattern matching automatable via xds.search_log + DataFrame filtering; Branch C requires xds-partition-state coding ability not yet available; Branch D XACServer search automatable; ICM transfer requires operator review; Step 5 ICM updates automatable)
MANUAL_FALLBACK: Search XDS logs manually for XACServer/TableMaster/Nephos.Account diagnostics, run Get-XdsPartition for FinalizeFailover XFiles check, classify root cause from known-issue matrix, then transfer ICM to owning team or RA XGeo DRI.
```

## Practical Handling Note (Multi-account Alerts)

In production incidents, a single `FailoverPendingTransaction` alert can contain multiple affected accounts in the same DGrep result set. The source TSG does not strictly define a fixed strategy for this case.

Recommended handling policy:

1. Use the incident title stuck signature (`PrimaryStuck.<Stage>` or `SecondaryStuck.<Stage>`) as the primary filter in Step 1.
2. If multiple accounts still match, sample a small set (for example 3 accounts) and run Steps 2-4 for each account.
3. Aggregate all sampled-account evidence into the incident update so escalation/transfer decisions are based on broader signal instead of a single account.

## Open Questions

| # | Question |
|---|---|
| 1 | ~~What is the canonical mapping from the human label `GeoHelper -> clean up rows in new tables to unblock failover` to extension name + operation id used by ACIS API?~~ **Resolved**: Geneva Action mitigation for XNamespaceDirectoryStatistics is no longer in the mitigation path for this TSG. The new flow diagnoses via XDS logs and transfers to owning teams. |
| 2 | ~~The source references a known-issue matrix image. Which additional `PrimaryStuck.PrepareFailover` signatures should branch to dedicated mitigations beyond `XNamespaceDirectoryStatistics`?~~ **Resolved**: The updated TSG defines four known-issue branches: (1) PrepareFailover with one side NotStarted → XACServer/TableMaster log diagnosis on NotStarted-side tenant → LLAM split or other split failure → transfer to StorageCRM or TableMaster; (2) Both PrepareFailover → Primary Nephos.Account GeoConfigOffCounter → RA XGeo DRI; (3) Both FinalizeFailover → XFiles partition GeoReplay:LiveReplay on Secondary → transfer to XStore/SMB; (4) Both DnsSwitch → XACServer 0x830a382d on Secondary → RA XGeo DRI. |
| 3 | Should incident auto-mitigation be blocked when stage is progressing but not yet complete, or is partial progress sufficient for this alert family? |
| 4 | Does `AccountFailoverStatisticsEvent` always include `operationId` as a filterable field in all clouds, or should fallback parsing be based on ActivityId correlation? |
| 5 | Is there a stable schema field for account name in `ServiceBackgroundActivityEvent`, or is message parsing always required? |
| 6 | Can `accountFailoverStatusType` transiently emit `Complete` for a prior operation id in the same window, requiring strict operation-id correlation? |
| 7 | ~~Are there cloud-specific stage values beyond the documented six states that require extending the ordering map?~~ **Resolved**: Yes — `DnsSwitch` has been added to the stage ordering between `PollFinalizeFailover` and `ShortTermCleanup` per the updated source TSG. |
| 8 | Is `ximi@microsoft.com` still the primary XGeo DRI route for this scenario in all regions and clouds? |
| 9 | What is the expected SLA for acknowledgment before secondary escalation to SRP leads is required? |
| 10 | ~~What is the exact XDS log search API for querying role-level verbose/error/perf logs?~~ **Resolved**: `await xds.search_log(tenant_name, from_time, to_time, role_instances, log_type=..., search_string=...)` from `xstore.common.xds`. See coding ability `xds-api-call`. |
| 11 | For the PrepareFailover diagnostic, what specific XACServer verbose log patterns indicate "quarantine cannot finish"? |
| 12 | For PollFailover GeoConfigOff diagnosis, is `GeoConfigOffCounter > 0` always sufficient, or are there thresholds or duration checks needed? |
| 13 | For the FinalizeFailover branch, what is the programmatic API equivalent of `Get-XdsPartition`? Is there a Python SDK method or must it be invoked via PowerShell remoting? |
| 14 | For the FinalizeFailover branch, what is the "versioned account name" format? Is it `<account_name>_v<version>` or another pattern? |
| 15 | ~~The previous Branch D (SoftFinalizeFailover) was in our decomposition speculatively. Is it still relevant?~~ **Resolved**: The updated source TSG does NOT include SoftFinalizeFailover as a known issue. It has been removed from the known-issue matrix. If SoftFinalizeFailover is stuck, it falls through to default escalation. |
