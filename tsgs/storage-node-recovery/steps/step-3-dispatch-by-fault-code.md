# Step 3 — Dispatch by fault code

> **Parent TSG**: [storage-node-recovery](../storage-node-recovery.md)
> **Maps to**: `_step_3_dispatch_by_fault_code()` method

## Purpose
Route to the appropriate fault-code-specific TSG based on the node's HI fault code.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `fault_code` | `int` | TSG input |
| `node_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `dispatched_to` | `str` | TSG name that was called, or `generic_recovery` |

## Processing Logic
1. Match `fault_code` against known FC-specific TSGs:

| Fault Code | TSG Folder |
|---|---|
| 8 | `storage-node-recovery-fc-8` |
| 70007 | `storage-node-recovery-fc-70007` |
| 43030 | `storage-node-recovery-fc-43030` |
| Other | Fall through to Step 4 (generic recovery) |

2. Call the matched TSG, passing `node_id`, `cluster_id`, `tenant_name`, `cloud_environment`.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: None (pure routing logic)
AUTOMATABLE: Yes (dispatch is a simple switch/match)
MANUAL_FALLBACK: DRI manually identifies fault code and follows the appropriate TSG.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Complete list of fault codes with dedicated TSGs? |
| 2 | Should unknown fault codes try generic recovery or immediately escalate? |
