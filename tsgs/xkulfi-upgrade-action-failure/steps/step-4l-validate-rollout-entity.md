# Step 4l — ValidateRolloutEntityOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [ValidateRolloutEntityOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/ValidateRolloutEntityOperation.md)
> **Maps to**: `_step_4l_validate_rollout_entity()`
> **Sample incident**: 701103648

## Purpose

A new VE (Virtual Environment) / PE has not been configured for rollout. Mitigation requires two repo PRs: `Azure-Gold-Config` and `Storage-XKulfi`. This branch produces a structured PR-template packet; it does not open the PRs.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `target_version`, `app` | `str` | Step 1 (the AP rollout title carries `app`, e.g., `APP~CEG_AZUREPIE-AZURECHAOSAGENT-VE`) |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `ve_name` | `str` | Extracted VE name (from `app` token) |
| `gold_config_pr_template` | `str` | Pre-filled instruction block referencing the sample PR |
| `xkulfi_pr_template` | `str` | Pre-filled instruction block referencing the sample PR |
| `mitigation_summary` | `str` | Combined PR packet |

## Processing Logic

1. Extract `ve_name` from the `app` field (strip `APP~` prefix if present).
2. Render two PR-template packets:
   - **`Azure-Gold-Config`**: edit `XStore-Global` VE → `environment.ini` → `Orchestration` section. Add settings `PreSelection`, `CheckFailingLimit`, `MaxScaleUnits`, `BatchSize`, `MaxBatchSize`, `SuccessThreshold`, `FailureThreshold`, `RolloutCompletionThreshold`. Reference [PR 941797](https://dev.azure.com/azureconfig/Gold/_git/Azure-Gold-Config/pullrequest/941797).
   - **`Storage-XKulfi`**: edit `StorageTenantGroupSettings.xml` → `ValidateRolloutEntityOperation.AllowedDeploymentEntities`; append the new VE. File must be **signed**. Reference [PR 13841810](https://msazure.visualstudio.com/One/_git/Storage-XKulfi/pullrequest/13841810).
3. After both PRs merge and data deployment completes, XKulfi auto-mitigates the incident. **Do not open PRs programmatically.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - GAP: no coding ability for opening ADO Git PRs (Azure-Gold-Config /
    Storage-XKulfi); the .xml file is signed, so signing flow blocks any
    automated commit.
AUTOMATABLE: Partially (template rendering).
MANUAL_FALLBACK: Engineer follows the PR-template packet to open both PRs.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is there a sanctioned signing flow for `StorageTenantGroupSettings.xml` that automation could invoke (HSM-backed?) — likely no, but worth confirming. |
| 2 | Are the 8 Orchestration settings (`PreSelection`, etc.) computable from defaults, or do they require human judgment per VE? |
