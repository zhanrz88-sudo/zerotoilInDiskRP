# Break Old Snapshot Families for Disk

## Metadata

| Field | Value |
|---|---|
| Source | OneNote: ComputeVM / Disks / ManagedDisksWiki / TSG.one |
| Date | October 3, 2024 |
| Owner | DiskRP / Disk Service |
| JIT Role | PlatformServiceOperator |
| Automatable | Partially (requires JIT approval + optional PM approval for ClearBilling) |

## Overview

This TSG is used to break old incremental snapshot families for a managed disk. Two use cases:

1. **Corruption recovery** — When snapshot corruption is detected and a new snapshot family must be started
2. **Leak unblock** — When XStore has leaks that cannot be fixed immediately, breaking the family unblocks operations

## Command

```powershell
Invoke-RemoveIncrementalSnapshotFamilyOnDisk -DiskName <DiskName> -SubscriptionId <SubscriptionId> -ResourceGroup <ResourceGroup> -Region <Region> [-ClearBilling]
```

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| DiskName | string | Yes | Name of the managed disk |
| SubscriptionId | GUID | Yes | Azure subscription ID |
| ResourceGroup | string | Yes | Resource group containing the disk |
| Region | string | Yes | Azure region (e.g., australiaeast) |
| ClearBilling | switch | No | Clear billing data. **Only use if PM explicitly requests it.** |

## Steps

1. Validate input parameters (DiskName, SubscriptionId, ResourceGroup, Region)
2. Check if ClearBilling is requested (requires PM approval)
3. Execute the Geneva Action via `RunXDiagCmdLetScript` or direct cmdlet invocation
4. Verify the action completed successfully
5. Post results to ICM incident

## Coding Ability Dependencies

- `geneva-action-call` — Execute the PowerShell cmdlet via Geneva Actions (ACIS)
- `icm-get-incident` — Fetch incident details and post results

## Safety Notes

- **ClearBilling** should ONLY be used when a PM explicitly requests it
- This is a **mutating** operation — it breaks the snapshot family permanently
- Requires **PlatformServiceOperator** JIT role
- In automation, may require elevated cert beyond `StoragePlatformServiceViewer`
