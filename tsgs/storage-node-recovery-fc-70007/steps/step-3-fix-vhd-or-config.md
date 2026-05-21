# Step 3 — Fix VHD or config file issues in MOS
> **Parent TSG**: [fc-70007-node-recovery](../fc-70007-node-recovery.md)
> **Maps to**: `_step_3_fix_vhd_or_config()` method

## Purpose
Apply the appropriate MOS-based fix based on diagnosed issue type.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `issue_type` | `str` | From Step 2 |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `recovered` / `sent_to_ofr` / `escalated` |

## Processing Logic
| Issue Type | Action |
|---|---|
| `zero_vhd_applications` | MOS → SAC → Shell → delete zero-size VHD from `C:\applications` → ReimageOS |
| `zero_vhd_repository` | Check `Get-Image` metadata → delete from `C:\applications` → ReimageOS |
| `config_corruption` | MOS → SAC → Shell → delete bad XML from `C:\config` → ReimageOS |
| `mos_unlock_timeout` | Follow Bitlocker unlock TSG |

ReimageOS via `RequestRepairActionFromMRDelegated`.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated, RequestRepairActionFromMRDelegated)
AUTOMATABLE: Partially (Geneva Actions automatable; file operations in MOS Shell are manual)
MANUAL_FALLBACK: DRI uses DCM Explorer PfAgent Shell.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can MOS Shell file operations be automated? |
