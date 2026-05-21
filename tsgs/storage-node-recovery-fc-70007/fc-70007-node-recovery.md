# FC 70007 — Storage Node Recovery

> **Source**: [Fault Code - 70007 | Storage Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%2070007%20-%20Node%20Recovery.md&_a=preview)

## Purpose

Recover storage nodes stuck in HumanInvestigate with fault code 70007 (WorkflowTimeout). Causes include file corruption, zero-size VHD files, config file issues, and MOS bitlocker unlock failures.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | Calling TSG (storage-node-recovery dispatch) |
| `cluster_id` | `str` | Calling TSG |
| `tenant_name` | `str` | Calling TSG |

## Outputs

| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `recovered` / `sent_to_ofr` / `escalated` |
| `issue_type` | `str` | `zero_vhd_applications` / `zero_vhd_repository` / `config_corruption` / `mos_unlock_timeout` / `unknown` |

## Steps

### Step 1 — Primary validation (Reset Health and Power Cycle)

[Step Analysis](steps/step-1-primary-validation.md)

Try simple recovery first:
1. Reset Node Health → `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`
2. Power Off → Reset → Power On → `PowerNodeWithSafetyChecksDelegated`

If node recovers → **done**. Otherwise continue to secondary validation.

> **Note**: This TSG does NOT apply to FC 70007 nodes where fault reason shows `PreparingEx` workflow timeout — those are a different issue.

### Step 2 — Diagnose issue type from node events

[Step Analysis](steps/step-2-diagnose-issue-type.md)

Check `$n.events` via FcShell to classify:

| Event Pattern | Issue Type |
|---|---|
| `StartingRole with: string.Empty` + role VHD info | VHD or config issue — continue to Step 3 |
| `PreparingEx` + `WorkflowTimeout` | Different issue — do NOT use this TSG |
| `MOSUnlockOsDrive` + timeout | Bitlocker unlock failure — follow [Bitlocker TSG](https://msazure.visualstudio.com/One/_wiki/wikis/One.wiki/37981/Unlock-bitlock-ed-blade-in-MOS) |

### Step 3 — Fix VHD or config file issues in MOS

[Step Analysis](steps/step-3-fix-vhd-or-config.md)

1. **Zero-size VHD in `C:\Applications`**: Move to HI → MOS → SAC → PfAgent Shell → delete zero-size VHD from `C:\applications` → ReimageOS via `RequestRepairActionFromMRDelegated`.
2. **Zero-size VHD in tenant repository**: Check via FcShell `Get-Image` → `$image.MetaData`. If zero → delete from `C:\applications` → ReimageOS.
3. **Config file corruption in `C:\Config`**: Move to MOS → delete bad config XML from `C:\config` → ReimageOS.

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PowerNodeWithSafetyChecksDelegated, PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated, RequestRepairActionFromMRDelegated)
AUTOMATABLE: Partially (primary validation automatable; secondary diagnosis requires FcShell/SAC; MOS file operations require Shell access)
MANUAL_FALLBACK: DRI uses FcShell for diagnosis, DCM Explorer for MOS and Shell access, Geneva Actions for recovery.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can FcShell `$n.events` be queried programmatically? |
| 2 | Can PfAgent Shell file operations (delete VHD, delete config) be executed via API? |
| 3 | Is there a Kusto-based alternative to `Get-Image` for checking VHD metadata? |
