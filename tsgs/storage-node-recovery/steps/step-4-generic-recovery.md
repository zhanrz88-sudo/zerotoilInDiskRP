# Step 4 — Generic recovery fallback

> **Parent TSG**: [storage-node-recovery](../storage-node-recovery.md)
> **Maps to**: `_step_4_generic_recovery()` method

## Purpose
Attempt generic recovery for nodes with unknown or uncovered fault codes using Reset Health and Power Cycle.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `cluster_id` | `str` | TSG input |
| `tenant_name` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `recovered` / `still_hi` / `escalated` |
| `actions_taken` | `list[str]` | Sequence of actions attempted |

## Processing Logic
1. **Reset Node Health** — `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`. Wait for node state transition.
2. **If still HI** — Power Cycle via `PowerNodeWithSafetyChecksDelegated` (Reboot and Power Cycle on fail), then Reset Health again.
3. **If still HI** — Escalate: Public → XSSE DRI on-call. AGC → `xsse-tented@microsoft.com`.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PowerNodeWithSafetyChecksDelegated)
AUTOMATABLE: Partially (Geneva Actions require SAW/dSTS auth; execution requires human approval gate)
RETRY_LOGIC: Reset Health → Power Cycle + Reset Health → Escalate
MAX_ATTEMPTS: 2 reset-health cycles
```

## Open Questions
| # | Question |
|---|---|
| 1 | What is the expected wait time between reset health and checking node state? |
| 2 | Should MOS boot be attempted as part of generic recovery, or only for specific fault codes? |
