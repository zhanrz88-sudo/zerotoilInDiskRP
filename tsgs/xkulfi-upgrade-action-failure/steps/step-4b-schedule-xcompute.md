# Step 4b — ScheduleXComputeJobsOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [ScheduleXComputeJobsOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/ScheduleXComputeJobsOperation.md)
> **Maps to**: `_step_4b_schedule_xcompute()`
> **Sample incident**: 455450715

## Purpose

XKulfi failed to schedule eligible XCompute jobs after rollout. Triage tenant state / DC freshness and produce mitigation packet (skip via DynamicSettingConfig).

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `xds_ui_reachable` | `bool \| None` | XDS UI / XCompute tab probe (read-only) |
| `dc_aligned_to_stg` | `bool \| None` | Whether tenant DC matches the rollout STG build |
| `mitigation_summary` | `str` | Suggested action / skip-config row |

## Processing Logic

1. **MXT triage**:
   - Probe tenant via `xds-api-call` (e.g., `RoleInstancesApi.role_instances_ping` for a representative role) — set `xds_ui_reachable`.
   - Compare tenant DC version to the target STG build (read-only check; flag mismatch).
2. **If DC outdated** → emit instruction "Update DC and wait for next retry" (manual; XKulfi auto-mitigates after success per `MitigateIncidentAfterSuccess=true`).
3. **Skip path (oncall)** — emit table row to insert into `DynamicSettingConfig`:

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `ScheduleXComputeJobsOperation.RetryCountBeforeSkip \| AppRollout` | `<deployment_id>` | `10` | `<alias>` |

   **Do not write the row programmatically.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - xds-api-call (RoleInstancesApi.role_instances_ping for tenant reachability)
  - GAP: no coding ability to read tenant DC version vs target STG build (need
    XKulfi/XDS API for DC version)
  - GAP: no coding ability for Azure Table writes (intentionally manual)
AUTOMATABLE: Partially.
  - Reachability probe + DC mismatch detection: target Yes (pending DC version API).
  - Skip-config write: No (manual, oncall-gated).
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall (Redmond) / yazzhang (Shanghai).
```

## Open Questions

| # | Question |
|---|---|
| 1 | Which API exposes "tenant DC version" so the parity check against the target STG build can be automated? |
| 2 | What constitutes "XCompute tab accessible" programmatically — is it a specific XDS endpoint? |
