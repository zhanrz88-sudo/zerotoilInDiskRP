# Step 1 — Acquire JIT access

> **Parent TSG**: [storage-node-recovery](../storage-node-recovery.md)
> **Maps to**: `_step_1_acquire_jit_access()` method

## Purpose
Request JIT access for FFE, XDS, and RDM required before executing any recovery actions.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `cluster_id` | `str` | TSG input |
| `tenant_name` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `jit_acquired` | `bool` | Whether JIT was successfully acquired |

## Processing Logic
1. Navigate to [aka.ms/JIT](https://aka.ms/JIT).
2. Request FFE / PlatformAdministrator for `<cluster_id>`.
3. Request XDS / Storage-PlatformServiceOperator for `<tenant_name>`.
4. Request RDM / RdmAdministrator for `<pf_cluster_name>`.
5. Wait for approval.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: None (JIT portal is manual)
AUTOMATABLE: No (JIT approval requires human interaction)
MANUAL_FALLBACK: Use JIT portal directly.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can JIT access be requested programmatically? |
