# Step 2 — Execute Geneva action
> **Parent TSG**: [mitigate-xnamespace-directorystatistics-block](../mitigate-xnamespace-directorystatistics-block.md)
> **Maps to**: `_step_2_execute_action()` method

## Purpose
Execute the GeoHelper cleanup action to unblock failover.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `versioned_account_name` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `ga_invocation_id` | `str` | Geneva action invocation id |

## Processing Logic
1. Submit Geneva action: Group=`GeoHelper`, Action=`clean up rows in new tables to unblock failover`.
2. Parameters: Tenant, TableName=`XNamespaceDirectoryStatistics`, AccountName=`<versioned_account_name>`.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (xportal.acis.submit)
AUTOMATABLE: Partially (technically automatable, requires validated operation-id mapping and approval)
```

## Open Questions
| # | Question |
|---|---|
| 1 | Exact ACIS extension and operation_id for this GeoHelper action? |
