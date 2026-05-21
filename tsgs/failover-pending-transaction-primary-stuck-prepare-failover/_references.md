# Shared References

## Kusto Endpoints

| Cloud | Cluster | Database | Notes |
|---|---|---|---|
| Public | `https://xcontrolplane.kusto.windows.net` | `SRP` | Optional fallback for SRP failover telemetry when DGrep linkage is insufficient. |
| USSec / USNat | `<environment-specific cluster>` | `SRP` | Confirm with on-call runbook before use. |

## DGrep Log Sources

| Namespace | Event Name | Purpose |
|---|---|---|
| `RegionalSRP` | `ServiceBackgroundActivityEvent` | Locate pending failover operation id from alert event payload. |
| `RegionalSRP` | `AccountFailoverEvent` | Determine whether failover reached `Complete`. |
| `RegionalSRP` | `AccountFailoverStatisticsEvent` | Determine Primary/Secondary stuck stage and progression. |

## XDS Log Sources (Step 4 Diagnostics)

| Role | Log Level | Purpose |
|---|---|---|
| `XACServer` | Verbose | Diagnose quarantine failures blocking PrepareFailover (Branch A); diagnose DnsSwitch container lock refresh failure `0x830a382d` (Branch D). |
| `TableMaster` | Error | Identify partition split failures (LLAM or other reasons) in Branch A. |
| `Nephos.Account` | Perf | Find `PollFailover` calls and check `GeoConfigOffCounter` when both sides at PrepareFailover (Branch B). |

## XDS Partition State (Step 4, Branch C)

| Command | Purpose |
|---|---|
| `Get-XdsPartition -Tenant <secondary_tenant> -Table XFiles -Account <versioned_account_name>` | Check XFiles partition state for `GeoReplay:LiveReplay` when both sides at FinalizeFailover. |

**Note**: No Python coding ability exists for `Get-XdsPartition` yet. This must be run via PowerShell or a future `xds-partition-state` coding ability.

## Known Error Patterns

| Pattern | Location | Meaning |
|---|---|---|
| `[LB:Split][Msg:Cannot split partition][Reason:Incompatible LLAM Stage]...[LLAMStage:LLAM_COMPLETE_PARTITION_HANDOFF_INTRA_CLUSTER]` | TableMaster error log | Partition split blocked by LLAM handoff — route to StorageCRM. |
| `[LB:Split][Msg:Cannot split partition][Reason:...]` (other reasons) | TableMaster error log | Partition split blocked by non-LLAM issue — route to TableMaster team. |
| `GeoConfigOffCounter=<x>` where `x > 0` | Nephos.Account perf log (PollFailover ActivityId trace) | GeoConfig not propagated — both sides at PrepareFailover — route to XGeo DRI. |
| `GeoReplay:LiveReplay` | XFiles partition state (Get-XdsPartition output) | XFile replayer blocked after finalize — route to XStore/SMB. |
| `[ACU][Failover][ORS] ExecuteJob: Failed to refresh containers lock for source account during failoveracuOp=InvalidAcuOp, accountName=<account name>, hr=0x830a382d` | XACServer verbose log (Secondary) | Container lock refresh failure during DnsSwitch — route to XGeo DRI. |

## Geneva Actions

_None used by this TSG. Previous mitigation via `GeoHelper -> clean up rows in new tables to unblock failover` has been superseded by XDS log diagnosis + ICM transfer._

## JIT Access Requirements

| Tool | Resource Type | Minimum Access |
|---|---|---|
| DGrep / SRP diagnostics | RegionalSRP telemetry | Read access |
| Geneva Action execution | ACIS / XStore action plane | Operator approval + action execution permission |
| ICM update/mitigate | ICM incident | Incident write permission |

## Dashboards and Portals

| Name | URL |
|---|---|
| DGrep portal | `https://portal.microsoftgeneva.com/logs/dgrep` |
| ICM incident portal | `https://portal.microsofticm.com/imp/v5/incidents/details/<incident_id>/summary` |

## Escalation Contacts

| Team | Contact / ICM Path | When to Engage |
|---|---|---|
| XGeo DRI | RA in ICM; `ximi@microsoft.com` (China working hours) | Default escalation for unknown stuck patterns; Both-PrepareFailover GeoConfigOff (Branch B); DnsSwitch container lock failure (Branch D). |
| Xstore/StorageCRM | ICM transfer to `Xstore/StorageCRM` | PrepareFailover stuck due to LLAM split block in TableMaster (Branch A). |
| Xstore/TableMaster | ICM transfer to `Xstore/TableMaster` | PrepareFailover stuck due to non-LLAM split failure in TableMaster (Branch A). |
| XStore/SMB | ICM transfer to `XStore/SMB` | FinalizeFailover stuck due to XFile replayer blocked (Branch C). |
| SRP on-call | `<region SRP on-call>` | If DGrep indicates SRP-side control-plane lock contention or operation conflicts. |

## Related External TSGs

| Title | Link |
|---|---|
| TSG: Failover Pending Transaction Taking Longer to Complete | `https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/srpdocs/failover/FailoverPendingTransaction-alert.md&_a=preview` |
| Failover blocked by XnamespaceDirectoryStatistics | `https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/Failover%20blocked%20by%20XnamespaceDirectoryStatistics.md&_a=preview` |
| Failover Operation Failures - 4XX Troubleshooting Guide | `https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/srpdocs/failover/FailoverAccount-4xxErrors.md&_a=preview` |
