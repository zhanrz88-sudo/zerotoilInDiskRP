# Step 4e — CheckRolePingBeforeUnprepareOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [CheckRolePingBeforeUnprepareOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/CheckRolePingBeforeUnprepareOperation.md)
> **Maps to**: `_step_4e_check_role_ping_before()`
> **Sample incident**: 493282112

## Purpose

Same as step-4d but the failure occurs **before** unpreparing UD (XKulfi holds and won't unprepare until the check passes). Triage and mitigation are identical.

## Inputs / Outputs / Processing Logic

Identical to [step-4d](step-4d-check-role-ping-after.md). The only difference is the `RowKey` operation prefix in the skip-config packet:

| PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
|---|---|---|---|---|
| `<tenant>` | `CheckRolePingBeforeUnprepareOperation.RetryCountBeforeSkip \| AppRollout \| <domain>` | `<deployment_id>` | `10` | `<alias>` |

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - xds-api-call (RoleInstancesApi.role_instances_ping)
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially (read-only confirmation).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall / yazzhang.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Same role-list extraction question as step-4d. |
| 2 | Is there a behavioral difference between Before/After variants that affects automation (e.g., different "freshness" tolerance for the role-ping result)? Source TSG implies "no". |
