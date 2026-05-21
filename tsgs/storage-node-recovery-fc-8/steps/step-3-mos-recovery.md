# Step 3 — Boot into MOS and redeploy OS

> **Parent TSG**: [fc-8-node-recovery](../fc-8-node-recovery.md)
> **Maps to**: `_step_3_mos_recovery()` method

## Purpose
Boot node into MOS, check agent status, and redeploy FullOS for a fresh GoalState attempt.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovered` | `bool` | Whether node reached Ready after OS redeploy |
| `new_fault_code` | `int \| None` | If node falls back to HI with a different FC |

## Processing Logic
1. Boot into MOS → `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated`.
2. Optional: reboot while in MOS.
3. Check DCM Agent status via SAC. If not started → restart RdAgent. If RdAgent running → Power Off/On.
4. Redeploy FullOS → `RequestRepairActionFromMRDelegated`.
5. Monitor: if Ready → done. If new FC (not 8 or 10033) → dispatch to that FC. If FC 8/10033 loop → continue to Step 4.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated, RequestRepairActionFromMRDelegated)
AUTOMATABLE: Partially (Geneva Actions automatable; SAC agent check is manual)
MANUAL_FALLBACK: DRI uses DCM Explorer for MOS boot and SAC agent check.
```

## Open Questions
| # | Question |
|---|---|
| 1 | How long to wait for MOS boot before checking agent status? |
