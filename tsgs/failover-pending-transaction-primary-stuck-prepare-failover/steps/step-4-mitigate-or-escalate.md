# Step 4 — Diagnose known issues and mitigate or escalate

> **Parent TSG**: [failover-pending-transaction-primary-stuck-prepare-failover](../failover-pending-transaction-primary-stuck-prepare-failover.md)
> **Maps to**: `_step_4_mitigate_or_escalate()` method

## Purpose

Diagnose the root cause of the stuck failover by searching XDS role-level logs on the correct side (primary or secondary tenant), classify it against the known-issue matrix, and route to the appropriate owning team via ICM transfer or escalation.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `stuck_location` | `str` | From Step 3 (`Primary`, `Secondary`, or `Unknown`) |
| `primary_stage` | `str` | From Step 3 |
| `secondary_stage` | `str` | From Step 3 |
| `effective_stuck_stage` | `str` | From Step 3 (`PrepareFailover`, `FinalizeFailover`, `DnsSwitch`, etc.) |
| `incident_id` | `int` | TSG input |
| `tenant_name` | `str` | TSG input (the SRP tenant; used to derive primary/secondary storage tenants) |
| `account_name` | `str` | From Step 1 |
| `operation_id` | `str` | From Step 1 |
| `evidence_links` | `list[str]` | DGrep links from prior steps |

## Outputs

| Field | Type | Description |
|---|---|---|
| `mitigation_status` | `str` | `Transferred` or `Escalated` |
| `mitigation_detail` | `str` | Description of action taken and target team |
| `xds_evidence_summary` | `str` | Key findings from XDS log search |
| `target_team` | `str` | ICM team the incident was routed to |

## Processing Logic

### Branch A — PrepareFailover with one side NotStarted

Triggered when: (`primary_stage == PrepareFailover` AND `secondary_stage == NotStarted`) OR (`primary_stage == NotStarted` AND `secondary_stage == PrepareFailover`).

**Key principle**: Go to the tenant with the **NotStarted** side for diagnostics.
- If `secondary_stage == NotStarted` → investigate on the **secondary** storage tenant
- If `primary_stage == NotStarted` → investigate on the **primary** storage tenant

1. **Search XACServer verbose log** — XDS log search for the account name in XACServer (Role) verbose log on the **NotStarted-side tenant**. Look for quarantine-related entries around the incident window.

2. **Check if quarantine cannot finish** — If XACServer log shows quarantine blocking, proceed to TableMaster diagnosis.

3. **Search TableMaster error log** — XDS log search for the account name in TableMaster (Role) error log on the **same NotStarted-side tenant**.

4. **Classify split failure**:

   | TableMaster Error Pattern | Action |
   |---|---|
   | `ERROR: XTableMaster.exe [LB:Split][Msg:Cannot split partition][Reason:Incompatible LLAM Stage]...[LLAMStage:LLAM_COMPLETE_PARTITION_HANDOFF_INTRA_CLUSTER]` (cannot split due to LLAM) | **Transfer ICM to Xstore/StorageCRM** |
   | `[LB:Split][Msg:Cannot split partition][Reason:...]` (cannot split for other reasons) | **Transfer ICM to Xstore/TableMaster** |

5. **Execute ICM transfer** — Add diagnostic summary to incident description, then transfer to the identified team.

### Branch B — Both sides at PrepareFailover (GeoConfigOff)

Triggered when: `primary_stage == PrepareFailover` AND `secondary_stage == PrepareFailover`.

**Key principle**: Go to the **Primary** tenant for diagnostics.

1. **Search Nephos.Account perf log** — XDS log search for the account name in Nephos.Account (Role) perf log on the **Primary** tenant. Expect multiple `PollFailover` call entries.

2. **Inspect a PollFailover call** — Pick one call randomly, follow its `ActivityId` to retrieve the full log trace.

3. **Check GeoConfigOffCounter** — Parse the full log for `GeoConfigOffCounter=<x>`. If `x > 0`, the issue is confirmed as a GeoConfig-Off scenario.

4. **Mitigate** — If `GeoConfigOffCounter > 0`, **RA XGeo DRI (Redmond working hours) / `ximi@microsoft.com` (China working hours)** via ICM. Add `GeoConfigOffCounter` evidence to incident description.

### Branch C — Both sides at FinalizeFailover (XFiles replayer blocked)

Triggered when: `primary_stage == FinalizeFailover` AND `secondary_stage == FinalizeFailover`.

**Key principle**: Go to the **Secondary** tenant for diagnostics.

1. **Get XFiles partition state** — Run PowerShell command:
   ```powershell
   $p = Get-XdsPartition -Tenant <secondary_tenant> -Table XFiles -Account <versioned_account_name>
   ```

2. **Check for GeoReplay:LiveReplay** — Inspect the partition state output. If any XFile partition is in `GeoReplay:LiveReplay` state, the issue is confirmed as XFile replayer blocked after finalize.

3. **Mitigate** — If confirmed, **transfer ICM to XStore/SMB**. Add partition state evidence to incident description. This is a known issue where XFile replayer gets blocked after finalize.

### Branch D — Both sides at DnsSwitch (container lock refresh failure)

Triggered when: `primary_stage == DnsSwitch` AND `secondary_stage == DnsSwitch`.

**Key principle**: Go to the **Secondary** tenant for diagnostics.

1. **Search XACServer verbose log for 0x830a382d** — XDS log search for `0x830a382d` in XACServer verbose log on the **Secondary** tenant.

2. **Confirm error pattern** — Expected log entry:
   ```
   INFO: XACServer.exe [ACU][Failover][ORS] ExecuteJob: Failed to refresh containers lock for source account during failoveracuOp=InvalidAcuOp, accountName=<account name>, hr=0x830a382d
   ```

3. **Mitigate** — If pattern confirmed, **RA XGeo DRI (Redmond working hours) / `ximi@microsoft.com` (China working hours)** via ICM. Add the error log evidence to incident description.

### Branch E — Default escalation

Triggered when the stuck stage/location does not match any known-issue pattern above (Branches A-D).

1. Build escalation summary: incident id, tenant, account name, operation id, stuck location/stage, primary_stage, secondary_stage, evidence links.
2. Add to ICM incident description.
3. **RA XGeo DRI (Redmond working hours) / `ximi@microsoft.com` (China working hours)** via ICM.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: xds-api-call (xstore.xds.search_log for XACServer verbose, TableMaster error, Nephos.Account perf; xds.search_by_activity_id for activity tracing; xds.generate_log_search_link for evidence links), xds-partition-state (Get-XdsPartition for XFiles partition state — coding ability NOT yet available), icm-get-incident (Incident.add_description, Incident.transfer)
AUTOMATABLE: Partially (Branches A, B, D: XDS log search and pattern matching automatable via xds.search_log + DataFrame filtering; Branch C: requires xds-partition-state coding ability not yet available — must be done manually or via PowerShell remoting; ICM transfer requires operator confirmation before execution)
MANUAL_FALLBACK: Search XDS logs manually via XInvestigator portal for the relevant role logs, run Get-XdsPartition manually for FinalizeFailover case, classify error pattern from the known-issue table, then transfer or RA via ICM portal.
```

## Open Questions

| # | Question |
|---|---|
| 1 | ~~What is the exact `xstore.xds` API for searching role-level logs?~~ **Resolved**: `await xds.search_log(tenant_name, from_time, to_time, role_instances, log_type=..., search_string=...)` from `xstore.common.xds`. Returns `XdsLogSearchEncapsulatedResult` with `.to_df()` method. See coding ability `xds-api-call`. |
| 2 | For XACServer verbose log, what specific patterns indicate "quarantine cannot finish"? Is there a known error code or message substring? |
| 3 | Are there additional TableMaster `[Reason:...]` values beyond LLAM that should route to StorageCRM instead of TableMaster? |
| 4 | For PollFailover GeoConfigOff, is `GeoConfigOffCounter > 0` always sufficient to trigger RA, or are there thresholds or age checks? |
| 5 | ~~Is `ximi@microsoft.com` still the primary XGeo DRI route?~~ Retained from parent TSG — still unresolved. |
| 6 | Which ICM team paths correspond to "Xstore/StorageCRM", "Xstore/TableMaster", and "XStore/SMB" for the transfer API? |
| 7 | For Branch C (FinalizeFailover), what is the programmatic API equivalent of `Get-XdsPartition`? Is there a Python SDK method in `xstore.common.xds` or must it be invoked via PowerShell remoting? This is a gap — no coding ability exists for this yet. |
| 8 | For Branch C, what is the "versioned account name" format required by `Get-XdsPartition`? Is it `<account_name>_v<N>` or derived from another source? |
| 9 | For Branch B, the source TSG says "go to primary" and search Nephos.Account perf log for PollFailover — but the previous decomposition had this as "PollFailover stuck on Secondary". The updated source is authoritative: both sides are at PrepareFailover, and diagnostics are on Primary. |
| 10 | For Branch A, how do we programmatically determine the secondary storage tenant name from the SRP tenant name? Is there a mapping API or naming convention (e.g., RSRP → storage tenant)? |
