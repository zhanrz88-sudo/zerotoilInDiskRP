# Step 1 — Classify disk fault type
> **Parent TSG**: [fc-43030-node-recovery](../fc-43030-node-recovery.md)
> **Maps to**: `_step_1_classify_fault_type()` method

## Purpose
Determine the specific disk failure sub-type from fault info and node diagnostics.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `fault_info` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `fault_type` | `str` | `missing_disk` / `persistent_memory` / `nvdimm_n` |

## Processing Logic
1. Parse `FaultInfo` for disk-related keywords.
2. If `Disks not found` or wrong model → `missing_disk`.
3. If `PhysicalDrive0` and small size (16/32 GB) → `persistent_memory`. Confirm via Kusto `LogNodeSnapshot`.
4. If no SAC post → `nvdimm_n`.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: kusto-query (LogNodeSnapshot for fault confirmation)
AUTOMATABLE: Partially (Kusto-based classification automatable; SAC check is manual)
```

## Open Questions
| # | Question |
|---|---|
| 1 | Complete list of FaultInfo patterns that map to each sub-type? |
