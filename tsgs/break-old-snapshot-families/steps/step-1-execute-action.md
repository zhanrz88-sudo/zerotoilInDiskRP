# Step 1: Validate Input and Execute Geneva Action

## Description

Extract disk parameters from the ICM incident (or manual input) and execute `Invoke-RemoveIncrementalSnapshotFamilyOnDisk` via Geneva Actions.

## Input Parameters

From incident title/description or manual input:
- DiskName
- SubscriptionId
- ResourceGroup
- Region
- ClearBilling (optional, default: false)

## Execution

The cmdlet `Invoke-RemoveIncrementalSnapshotFamilyOnDisk` is a PowerShell cmdlet executed via the `RunXDiagCmdLetScript` Geneva Action on the `Xstore` extension.

### Geneva Action Parameters

```python
extension_name = "Xstore"
operation_id = "RunXDiagCmdLetScript"
params = [
    "Invoke-RemoveIncrementalSnapshotFamilyOnDisk",
    json.dumps([
        ["DiskName", disk_name],
        ["SubscriptionId", subscription_id],
        ["ResourceGroup", resource_group],
        ["Region", region],
        # ["ClearBilling", "true"]  # Only if PM-approved
    ])
]
```

## Safety

- **APPROVAL REQUIRED** before execution — this is a destructive action
- ClearBilling requires **explicit PM approval** — never auto-add this flag
- Requires PlatformServiceOperator JIT

## CODING_ABILITY_DEPENDENCY: geneva-action-call (acis.submit, acis.get_result)
## AUTOMATABLE: Partially (requires JIT + human approval gate for ClearBilling)
