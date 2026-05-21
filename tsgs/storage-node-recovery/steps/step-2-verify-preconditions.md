# Step 2 — Verify preconditions

> **Parent TSG**: [storage-node-recovery](../storage-node-recovery.md)
> **Maps to**: `_step_2_verify_preconditions()` method

## Purpose
Ensure safety preconditions are met before attempting node recovery.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `node_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `du_active` | `bool` | Whether a DU is active on the tenant |
| `deployment_active` | `bool` | Whether a deployment is active |
| `safe_to_proceed` | `bool` | Whether recovery can proceed |

## Processing Logic
1. Check if a DU is active on the tenant — if so, follow DU TSG instead.
2. Check if a deployment is active on the same UD — if so, coordinate with `xdep@microsoft.com`.
3. Ensure only one node per tenant is being worked at a time.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: xds-api-call (UpgradeStateApi.upgrade_state_get_upgrade_state), kusto-query (DU status check)
AUTOMATABLE: Yes (read-only checks)
MANUAL_FALLBACK: Check XDS Upgrade State tab and DU dashboard manually.
```

## Open Questions
| # | Question |
|---|---|
| 1 | How to detect active DU programmatically? |
| 2 | Is there a lock mechanism to enforce one-node-at-a-time per tenant? |
