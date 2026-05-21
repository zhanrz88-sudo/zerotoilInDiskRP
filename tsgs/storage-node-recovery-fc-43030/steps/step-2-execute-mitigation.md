# Step 2 — Execute fault-type-specific mitigation
> **Parent TSG**: [fc-43030-node-recovery](../fc-43030-node-recovery.md)
> **Maps to**: `_step_2_execute_mitigation()` method

## Purpose
Apply the correct mitigation based on classified disk fault type.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `fault_type` | `str` | From Step 1 |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `gdco_ticket_created` / `bios_flavor_reset` / `ofr_for_nvdimm` |

## Processing Logic
| Fault Type | Action |
|---|---|
| `missing_disk` | GDCO SKU check → DISKPART comparison → OFR → escalate GDCO |
| `persistent_memory` | BIOS flavor reset (needs XSSE DRI approval) → Repave |
| `nvdimm_n` | OFR with FC 60400 → vendor inspection → breakfix if NVDIMM |

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (RequestRepairActionFromMRDelegated), kusto-query (dcmInventoryComponentDiskWmi)
TSG_CALL: escalate-gdco-tickets
AUTOMATABLE: Partially (Repave automatable; BIOS reset needs approval; DISKPART is manual)
APPROVAL_GATE: BIOS flavor reset requires XSSE DRI approval
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can BIOS flavor reset be triggered via API? |
| 2 | Can SKU → expected disk mapping be queried programmatically from GDCO Inventory? |
