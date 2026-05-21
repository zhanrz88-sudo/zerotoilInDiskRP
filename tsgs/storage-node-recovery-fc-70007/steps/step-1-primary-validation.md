# Step 1 — Primary validation
> **Parent TSG**: [fc-70007-node-recovery](../fc-70007-node-recovery.md)
> **Maps to**: `_step_1_primary_validation()` method

## Purpose
Attempt simple recovery before diagnosing specific 70007 sub-types.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovered` | `bool` | Whether node reached Ready |

## Processing Logic
1. Reset Node Health → `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`.
2. If still HI: Power Off → Reset → Power On via `PowerNodeWithSafetyChecksDelegated`.
3. If recovered → done. Otherwise continue.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PowerNodeWithSafetyChecksDelegated)
AUTOMATABLE: Yes (with approval gate)
```

## Open Questions
| # | Question |
|---|---|
| 1 | Wait time between reset health and state check? |
