# Step 2 — Diagnose issue type from node events
> **Parent TSG**: [fc-70007-node-recovery](../fc-70007-node-recovery.md)
> **Maps to**: `_step_2_diagnose_issue_type()` method

## Purpose
Classify the specific 70007 sub-type from FcShell node events.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `cluster_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `issue_type` | `str` | `zero_vhd_applications` / `zero_vhd_repository` / `config_corruption` / `mos_unlock_timeout` / `unknown` |

## Processing Logic
1. FcShell: `$n = $f | Get-node "<node_id>"` → `$n.events`
2. Pattern match:
   - `StartingRole with: string.Empty` → VHD/config issue
   - `PreparingEx` + `WorkflowTimeout` → NOT this TSG
   - `MOSUnlockOsDrive` timeout → Bitlocker issue

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: None (FcShell is interactive — no known API)
AUTOMATABLE: No (FcShell requires SAW interactive session)
MANUAL_FALLBACK: DRI uses FcShell on SAW.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can FcShell node events be queried via Kusto or API instead? |
