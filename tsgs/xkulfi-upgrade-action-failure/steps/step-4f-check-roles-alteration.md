# Step 4f — CheckRolesAlterationOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [CheckRolesAlterationOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/CheckRolesAlterationOperation.md)
> **Maps to**: `_step_4f_check_roles_alteration()`
> **Sample incident**: 590196527

## Purpose

The new STG version removes a role, adds role-instance count, or removes role-instance count. Deployment is blocked after upgrade and before unpreparing the first UD. Default response: cancel the deployment; only allow via skip-config when intentional.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `domain` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `alteration_kind` | `str \| None` | `RemoveRole` \| `AddInstanceCount` \| `RemoveInstanceCount` (parsed from logs/info) |
| `affected_role` | `str \| None` | E.g., `XFENativeBlob` |
| `mitigation_summary` | `str` | Suggested action — default: cancel rollout |

## Processing Logic

1. Parse `alteration_kind` and `affected_role` from `dgrep_rows` / Troubleshooting info.
2. **Default mitigation**: locate the engineer who triggered the deployment and ask them to cancel. Or escalate to `liuzhouchen` (Shanghai). **Do not auto-cancel.**
3. **If intentional** (oncall path): emit table row matching the alteration kind:

   | Alteration | RowKey config |
   |---|---|
   | RemoveInstanceCount | `CheckRolesAlterationOperation.AllowRemoveInstanceOfRoles \| AppRollout \| <domain>` |
   | AddInstanceCount | `CheckRolesAlterationOperation.AllowAddInstanceOfRoles \| AppRollout \| <domain>` |
   | RemoveRole | `CheckRolesAlterationOperation.AllowRemoveRoles \| AppRollout \| <domain>` |

   `Value` example: `<string>XFENativeBlob</string>`. **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - GAP: no coding ability to look up "who triggered this deployment" (needs
    XKulfi rollout-trigger metadata API)
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially (parse alteration_kind / affected_role).
MANUAL_FALLBACK: Escalate to liuzhouchen (Shanghai) or XStore/Deployment oncall.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Where is "who triggered the deployment" recorded (XKulfi rollout table?) — needed to auto-tag the ICM with the deployment owner. |
| 2 | Source's "AllowRemoveInstanceOfRoles" PartitionKey row in the example also includes `| 2` (a domain index) but other examples don't — confirm whether the domain suffix is required for this config family. |
