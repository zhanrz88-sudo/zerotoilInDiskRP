# Step 4k — ValidateBuildOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [ValidateBuildOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/ValidateBuildOperation.md)
> **Maps to**: `_step_4k_validate_build()`
> **Sample incident**: 455672116

## Purpose

Pre-rollout build validation failed (empty build, downgrade attempt, or unexpected exception). Default response: cancel rollout if downgrade; otherwise collect logs and escalate.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `target_version` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `failure_kind` | `str \| None` | `EmptyBuild` \| `Downgrade` \| `Exception` (parsed from logs) |
| `current_build_version` | `str \| None` | If detectable from logs |
| `mitigation_summary` | `str` | Instruction packet |

## Processing Logic

1. Classify `failure_kind` from `dgrep_rows`.
2. **If `Downgrade`** → instruction: follow [How to abort an AppRollout](https://msazure.visualstudio.com/One/_wiki/wikis/XKulfi/160614/AppRollout-manual-actions?anchor=how-to-abort-an-approllout%3F). For Preprod personal-test downgrade, confirm with tenant owner.
3. **If `EmptyBuild` and tenant in newly-added cluster** → ask `yazzhang` to follow up with OM team.
4. **If `Exception`** (oncall) → file a bug.
5. Skip-config row template (oncall, last resort):

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `ValidateBuildOperation.RetryCountBeforeSkip \| AppRollout` | `<deployment_id>` | `10` | `<alias>` |

   **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - GAP: no coding ability to compare target build vs current tenant build (needs
    XKulfi/STG metadata API)
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially (failure-kind classification from logs).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall / yazzhang.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Which API returns the current STG version for a tenant so the Downgrade detection can be deterministic instead of regex on log strings? |
