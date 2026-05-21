# Step 4c — UpdateStgVersionOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [UpdateStgVersionOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/UpdateStgVersionOperation.md)
> **Maps to**: `_step_4c_update_stg_version()`
> **Sample incident**: 451853863

## Purpose

XKulfi failed to update STG versions in metadata after rollout. Triage tenant state and DC freshness; produce skip mitigation packet.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `xds_ui_reachable` | `bool \| None` | Tenant probe |
| `dc_aligned_to_stg` | `bool \| None` | DC parity with target STG |
| `error_signature` | `str \| None` | Common: `System.ServiceModel.FaultException: Error saving dynamic config` |
| `mitigation_summary` | `str` | Suggested action / skip-config row |

## Processing Logic

1. Same MXT triage as step-4b: tenant reachability + DC parity + recent smoke / EnPns sanity.
2. Extract `error_signature` from `dgrep_rows` if present.
3. Skip-config row template:

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `UpdateStgVersionOperation.RetryCountBeforeSkip \| AppRollout` | `<deployment_id>` | `10` | `<alias>` |

   **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - xds-api-call (tenant reachability)
  - GAP: DC version API (same as step-4b)
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially (read-only triage).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall / yazzhang.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Same DC-version API gap as step-4b. |
| 2 | Is "EnPns" something we can probe programmatically (XDS endpoint)? |
