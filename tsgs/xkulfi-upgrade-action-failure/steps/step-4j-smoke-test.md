# Step 4j — SmokeTestOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [SmokeTestOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/SmokeTestOperation.md)
> **Maps to**: `_step_4j_smoke_test()`
> **Sample incident**: 489230068

## Purpose

No smoke test passed for the configured retry count. XKulfi holds the deployment until smoke passes. Triage = inspect failing smoke cases via XDS UI history, then defer to Fabric Master TSG.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `domain`, `target_version` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `failing_cases` | `list[str]` | E.g., `HealthChecksSuite/Async Non-Critical Storage Roles Quorum Check` |
| `mitigation_summary` | `str` | Triage packet referencing Fabric Master TSG + skip-config row |

## Processing Logic

1. Parse `failing_cases` from `dgrep_rows` (or recommend XDS UI smoke history if unparseable).
2. Emit instruction set:
   - "Open XDS UI smoke history; check failing cases."
   - "Follow Fabric Master TSG: [Master TSG link](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/stgos/incidents/_master_tsg)."
   - "If lease owner approves skip → escalate to XStore/Deployment / yazzhang."
3. Skip-config row template:

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `SmokeTestOperation.RetryCountBeforeSkip \| AppRollout \| <domain>` | `<deployment_id>` | `10` | `<alias>` |

   **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - xds-api-call (smoke history endpoint — verify availability)
  - GAP: DynamicSettingConfig write (manual)
  - DELEGATION: deeper smoke-failure RCA delegated to Fabric Master TSG (out of scope here)
AUTOMATABLE: Partially (failing-case parse).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall / yazzhang.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Which `xds-api-call` endpoint returns smoke history for a tenant (last N runs, per-case pass/fail)? |
| 2 | Should this branch eventually call into a separate "fabric-smoke-failure" TSG class once that's authored? |
