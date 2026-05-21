# Step 2 — Simple recovery (Reboot and Reset Health)

> **Parent TSG**: [fc-8-node-recovery](../fc-8-node-recovery.md)
> **Maps to**: `_step_2_simple_recovery()` method

## Purpose
Attempt the simplest recovery path: power cycle and reset health.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `network_ok` | `bool` | From Step 1 |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovered` | `bool` | Whether node reached Ready state |

## Processing Logic
1. Check that affected nodes aren't all in the same rack (could be power/TOR issue).
2. Power Off → `PowerNodeWithSafetyChecksDelegated`
3. Reset Health → `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`
4. Power On → `PowerNodeWithSafetyChecksDelegated`
5. Alternative: `SAC> restart` then Reset Health.
6. If node recovers to Ready → done.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (PowerNodeWithSafetyChecksDelegated, ResetNodeHealthWithSafetyChecksCrossServiceDelegated)
AUTOMATABLE: Yes (with human approval gate for Geneva Actions)
MANUAL_FALLBACK: Execute Geneva Actions from portal.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Expected wait time after power cycle before checking node state? |
