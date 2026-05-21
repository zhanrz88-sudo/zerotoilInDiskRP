# Storage Node Recovery — Overview and Dispatch

> **Source**: [Storage Node Recovery — JIT Access and Precautions](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/Storage%20Node%20Recovery.md&_a=preview)

## Purpose

Entry point for all storage node recovery scenarios. Establishes JIT access prerequisites, safety precautions, and dispatches to the appropriate fault-code-specific TSG based on the node's HI fault code.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | Calling TSG (e.g., CSM quorum loss Step 4) |
| `cluster_id` | `str` | Derived from node context |
| `tenant_name` | `str` | Calling TSG |
| `fault_code` | `int` | From Kusto/FcShell fabric state |
| `cloud_environment` | `str` | `Public` / `USSec` / `USNat` |

## Outputs

| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `recovered` / `still_hi` / `sent_to_ofr` / `escalated` |
| `actions_taken` | `list[str]` | Sequence of recovery actions attempted |

## Steps

### Step 1 — Acquire JIT access

[Step Analysis](steps/step-1-acquire-jit-access.md)

Request JIT access via [aka.ms/JIT](https://aka.ms/JIT):

| Resource Type | Instance | Access Level |
|---|---|---|
| FFE | `<cluster_id>` | PlatformAdministrator |
| XDS | `<tenant_name>` | Storage-PlatformServiceOperator |
| RDM | `<pf_cluster_name>` | RdmAdministrator |

### Step 2 — Verify preconditions

[Step Analysis](steps/step-2-verify-preconditions.md)

1. Work on **one node per tenant** at a time.
2. Check for active DU on tenant — if DU active, follow [DU TSG](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Data%20Unavailability%20Alert%20%28DU%29.md&_a=preview) instead.
3. Check for active deployment — if deployment active on same UD, coordinate with `xdep@microsoft.com`.

### Step 3 — Dispatch to fault-code-specific TSG

[Step Analysis](steps/step-3-dispatch-by-fault-code.md)

| Fault Code | TSG | Description |
|---|---|---|
| FC 8 | **Calls**: [fc-8-node-recovery](../storage-node-recovery-fc-8/fc-8-node-recovery.md) | Generic — motherboard, DAC cable, PfAgent issues |
| FC 70007 | **Calls**: [fc-70007-node-recovery](../storage-node-recovery-fc-70007/fc-70007-node-recovery.md) | Workflow timeout — file corruption, VHD, config issues |
| FC 43030 | **Calls**: [fc-43030-node-recovery](../storage-node-recovery-fc-43030/fc-43030-node-recovery.md) | Disk failure — missing/wrong disk, persistent memory |
| Other | Attempt generic recovery (Reset Health → Power Cycle → Escalate) | Unknown fault codes |

### Step 4 — Generic recovery fallback (for unknown fault codes)

[Step Analysis](steps/step-4-generic-recovery.md)

For fault codes not covered by specific TSGs:

1. **Reset Node Health** — Geneva Action: `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`
2. **Power Cycle + Reset** — If still HI: `PowerNodeWithSafetyChecksDelegated` (Reboot and Power Cycle on fail), then Reset Health again.
3. **Escalate** — If still HI: Public → XSSE DRI on-call. AGC → `xsse-tented@microsoft.com`.

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PowerNodeWithSafetyChecksDelegated, PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated), kusto-query (GetAllStorageNodeFabricHealth)
TSG_CALL: storage-node-recovery-fc-8, storage-node-recovery-fc-70007, storage-node-recovery-fc-43030
AUTOMATABLE: Partially (JIT acquisition manual; generic Reset/PowerCycle automatable with approval gate; fault-code-specific recovery varies)
MANUAL_FALLBACK: Use FcShell for node state, DCM Explorer for SAC, Geneva Actions portal for recovery.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Complete list of fault codes that have dedicated TSGs beyond FC 8, 70007, 43030? |
| 2 | Can JIT access be acquired programmatically, or is it always a manual portal step? |
| 3 | How to detect active DU programmatically to enforce the precondition? |
