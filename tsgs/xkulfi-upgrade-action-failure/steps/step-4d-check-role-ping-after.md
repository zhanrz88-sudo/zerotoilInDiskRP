# Step 4d — CheckRolePingAfterUnprepareOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [CheckRolePingAfterUnprepareOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/CheckRolePingAfterUnprepareOperation.md)
> **Maps to**: `_step_4d_check_role_ping_after()`
> **Sample incident**: 491737669

## Purpose

Too many role instances in the batch became unresponsive **after** unpreparing UD. Confirm via XDS role ping, suggest restart, or emit skip-config packet.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `domain`, `target_version` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `unresponsive_roles` | `list[str]` | Role-instance names parsed from Troubleshooting info / DGrep |
| `confirmed_unresponsive` | `list[str]` | Subset confirmed by XDS role ping |
| `mitigation_summary` | `str` | Suggested action / skip-config row |

## Processing Logic

1. Parse the unresponsive role-instance list from `dgrep_rows` (or from the incident's Troubleshooting info if log scrape can read it).
2. For each, run `xds-api-call` `RoleInstancesApi.role_instances_ping` (read-only) to confirm.
3. **MXT path**: For Preprod, suggest "restart unresponsive roles first; investigate logs if still unresponsive". For Canary/Prod, do not auto-act — escalate.
4. **DM repair path**: If machines are unhealthy, note that DM auto-initiates repair; do nothing.
5. **Skip path (oncall)** — table row template:

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `CheckRolePingAfterUnprepareOperation.RetryCountBeforeSkip \| AppRollout \| <domain>` | `<deployment_id>` | `10` | `<alias>` |

   **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - xds-api-call (RoleInstancesApi.role_instances_ping — read-only confirmation)
  - GAP: programmatic role restart is intentionally NOT enabled here (mutates prod;
    even Preprod restart requires human judgment per source TSG).
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially.
  - Parse + confirm unresponsive list: Yes.
  - Restart roles / write skip config: No (manual).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall / yazzhang.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Does the Troubleshooting info list of unresponsive roles appear in DGrep rows, or only in the incident HTML body? Affects whether `unresponsive_roles` can be extracted without an ICM-page scraper. |
