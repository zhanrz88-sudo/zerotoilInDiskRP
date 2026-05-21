# Step 4g — DeploySecretsOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [DeploySecretsOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/DeploySecretsOperation.md)
> **Maps to**: `_step_4g_deploy_secrets()`
> **Sample incident**: 455401851

## Purpose

XKulfi failed to deploy secrets for the target STG binary (often a `Microsoft.WindowsAzure.Security.CredentialsManagement.SecretsConfig.SecretsConfigLibException`). Mostly mitigated by the skip-config when the build adds no new secrets.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `error_signature` | `str \| None` | E.g., `SecretsConfigLibException: ...` |
| `mitigation_summary` | `str` | Skip-config row + bug-filing recommendation |

## Processing Logic

1. Extract `error_signature` from `dgrep_rows`.
2. Emit MXT instruction: collect logs + escalate to oncall.
3. Oncall path:
   - "If issue occurs frequently, open a bug item."
   - "If no new secret was added in the target STG build (~99%), skip via DynamicSettingConfig."
4. Skip-config row template:

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `DeploySecretsOperation.RetryCountBeforeSkip \| AppRollout` | `<deployment_id>` | `10` | `<alias>` |

   **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - GAP: no coding ability to compare "secrets in target STG" vs "secrets in current STG"
    (would need a secrets manifest diff API)
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially (signature extraction only).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall / yazzhang.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is there a manifest API or repo path that lists secrets per STG build, so the "no new secrets" check could be automated? |
