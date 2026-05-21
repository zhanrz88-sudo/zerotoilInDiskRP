# XKulfi UpgradeActionFailure

> **Source**: [UpgradeActionFailure/index.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/index.md)
> **Owning team**: `XStore/Deployment` (XKulfi)
> **Default severity**: Sev3 (`UpgradeActionIncidentSeverity`)
> **Alert keyword**: `XKulfiAutoAlert` (`UpgradeActionIncidentKeyword`)
> **Configuration reference**: [eng.ms ConfigurationInstructions](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/xpfdeployment/xkulfi/operation_document/configurationinstructions)

## Purpose

XKulfi runs many `UpgradeAction`s during every STG rollout, AP control plane rollout, and OS upgrade. Each execution is a `job`. When an action keeps failing/faulted past `RetryCountBeforeAlert` (default 3), XKulfi raises an `UpgradeActionFailure` incident and holds the rollout. This TSG parses the incident, fetches failure logs, and dispatches to the right per-operation mitigation.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `str` | ICM alert |
| `time_window_hours` | `int` | Default `6`; used for DGrep log query window |

## Outputs

| Field | Type | Description |
|---|---|---|
| `tenant` | `str` | Tenant name parsed from the title (virtual tenant for ZRS) |
| `operation` | `str` | UpgradeAction operation name (e.g., `PrepareBatchOperation`) |
| `rollout_type` | `str` | `ApServiceRollout`, `AppRollout`, or `OsUpgrade` |
| `deployment_id` | `str` | Group rollout id (e.g., `01DA89CBF0EC9A0B:11647`) |
| `domain` | `str \| None` | UD or FD identifier (domain-level operations only) |
| `target_version` | `str \| None` | E.g., `RELEASE_STG95/95.9.33.0` (when present) |
| `failure_logs` | `list[dict]` | Recent DGrep error rows |
| `branch_taken` | `str` | Which step-4 branch was selected |
| `mitigation_summary` | `str` | Human-readable suggested action (or escalation package) |

## Operation matrix

Operations covered by this TSG family. "Has dedicated sub-step" means the source repo has a per-operation md page.

### Deployment-level (run once per rollout)

| Operation | Has dedicated sub-step? |
|---|---|
| `CheckLeftOverMachinesBeforeUnbookOperation` | No |
| `CheckRolesAlterationOperation` | Yes — [step-4f](steps/step-4f-check-roles-alteration.md) |
| `ClearPastRolloutAlertsOperation` | No |
| `DeploySecretsOperation` | Yes — [step-4g](steps/step-4g-deploy-secrets.md) |
| `ResetWatchdogConfigOperation` | No |
| `ScheduleXComputeJobsOperation` | Yes — [step-4b](steps/step-4b-schedule-xcompute.md) |
| `TenantHealthSignOffOperation` | No |
| `UpdateConfigurationStorageVersionOperation` | No |
| `UpdateDynamicConfigSchemaOperation` | No |
| `UpdateStgVersionOperation` | Yes — [step-4c](steps/step-4c-update-stg-version.md) |
| `ValidateBuildOperation` | Yes — [step-4k](steps/step-4k-validate-build.md) |
| `ValidateRolloutEntityOperation` | Yes — [step-4l](steps/step-4l-validate-rollout-entity.md) |

### Domain (UD/FD)-level (run per batch)

| Operation | Has dedicated sub-step? |
|---|---|
| `CheckOSVersionMismatchedOperation` | No |
| `CheckRolePingAfterUnprepareOperation` | Yes — [step-4d](steps/step-4d-check-role-ping-after.md) |
| `CheckRolePingBeforeUnprepareOperation` | Yes — [step-4e](steps/step-4e-check-role-ping-before.md) |
| `MonitorUpgradeBatchProgressOperation` | Yes — [step-4h](steps/step-4h-monitor-upgrade-batch-progress.md) |
| `PostPrepareBatchOperation` | Yes — [step-4i](steps/step-4i-post-prepare-batch.md) |
| `PrepareBatchOperation` | Yes — [step-4a](steps/step-4a-prepare-batch.md) |
| `SmokeTestOperation` | Yes — [step-4j](steps/step-4j-smoke-test.md) |

Operations without a dedicated sub-step fall through to [step-4z generic escalation](steps/step-4z-generic-escalation.md).

## Common config knobs (`DynamicSettingConfig` defaults)

| Knob | Default | Notes |
|---|---|---|
| `TimeoutInSeconds` | `900` | Per-job timeout |
| `RetryCountBeforeAlert` | `3` | Failures before incident raised |
| `RetryCountBeforeSkip` | `-1` | `-1` = never auto-skip; oncall sets to `0`/job-count to skip |
| `RetryBakeTimeInSeconds` | `0` | |
| `MitigateIncidentAfterSuccess` | `true` | Auto-mitigate when next attempt passes |
| `MitigateIncidentAfterDelayInSeconds` | `300` | |
| `UpgradeActionIncidentOwningTeamId` | (XStore/Deployment) | |
| `UpgradeActionIncidentSeverity` | `3` | |
| `UpgradeActionIncidentKeyword` | `XKulfiAutoAlert` | |
| `CaptureBeginEndEvents` | `true` | |
| `CaptureInProgressEvent` | `true` | |
| `ApplicableToApServiceRollout` | `false` | |

`DynamicSettingConfig` schema: `PartitionKey = <Tenant>`, `RowKey = <Operation>.<Config> | <RolloutType> [| <Domain>]?`, plus `DeploymentId`, `Value`, `UpdatedBy`, `ValidBefore`. See [_references.md](_references.md).

## Where to read failure logs

1. **DGrep** — click "Retrieve logs by the alert keyword" on the incident; filters on `XKulfiAutoAlert` + tenant + window.
2. **History job results** — XDS UI ▸ Tenant Utils ▸ XLock Tool ▸ XDS ▸ `upgradetool` ▸ `upgradecpeevents` ▸ pick the operation.
3. **Blob XML** — storage account `xdashxstorepublicpf`, container `xkulfi`, path `TenantStatus/<tenant-or-virtual-tenant>/<operation>` (XML).

## Steps

### Step 1 — Parse incident

Parse the ICM incident title to extract `tenant`, `operation`, `rollout_type`, `deployment_id`, optional `domain`, optional `target_version`. Title patterns observed:

- `[<Operation>=[[XKulfi]<Tenant>-<RolloutType>-<DeploymentId>][<TargetVersion>][UpgradeDomain=<N>][<UTC time>]]`
- `[<Operation>=<DeploymentId>]` (older, no domain/version)
- AP rollout form: `[OperationName=<Op>][ActionKey=<Tenant>;<DeploymentId>;<App>;<Version>]`

[Step Analysis](steps/step-1-parse-incident.md)

### Step 2 — Fetch failure logs

Run DGrep with the alert-keyword query for the tenant and time window; collect the most recent failed-job rows (timestamp, exception type, message). Optionally read the per-operation history XML from blob `xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/<operation>`. [Step Analysis](steps/step-2-fetch-failure-logs.md)

### Step 3 — Route by operation

Look up `operation` in the routing table below and dispatch to the matching step-4 branch. Unknown operations fall through to [step-4z](steps/step-4z-generic-escalation.md).

| Operation | Branch |
|---|---|
| `PrepareBatchOperation` | [step-4a](steps/step-4a-prepare-batch.md) |
| `ScheduleXComputeJobsOperation` | [step-4b](steps/step-4b-schedule-xcompute.md) |
| `UpdateStgVersionOperation` | [step-4c](steps/step-4c-update-stg-version.md) |
| `CheckRolePingAfterUnprepareOperation` | [step-4d](steps/step-4d-check-role-ping-after.md) |
| `CheckRolePingBeforeUnprepareOperation` | [step-4e](steps/step-4e-check-role-ping-before.md) |
| `CheckRolesAlterationOperation` | [step-4f](steps/step-4f-check-roles-alteration.md) |
| `DeploySecretsOperation` | [step-4g](steps/step-4g-deploy-secrets.md) |
| `MonitorUpgradeBatchProgressOperation` | [step-4h](steps/step-4h-monitor-upgrade-batch-progress.md) |
| `PostPrepareBatchOperation` | [step-4i](steps/step-4i-post-prepare-batch.md) |
| `SmokeTestOperation` | [step-4j](steps/step-4j-smoke-test.md) |
| `ValidateBuildOperation` | [step-4k](steps/step-4k-validate-build.md) |
| `ValidateRolloutEntityOperation` | [step-4l](steps/step-4l-validate-rollout-entity.md) |
| (anything else) | [step-4z](steps/step-4z-generic-escalation.md) |

[Step Analysis](steps/step-3-route-by-operation.md)

### Step 4 — Operation-specific branch

Execute the branch from Step 3. Each branch produces a `mitigation_summary` containing:

- A diagnostic verdict (e.g., "XDS preparation timeout on `CheckQuorumTask::XvExtentManagerRole`")
- Suggested next action (read-only) OR a manual mitigation packet (table row to insert, blob XML edit, repo PR template, "Skip Current Task" instruction)
- Escalation contacts

Branches must NOT auto-write the `DynamicSettingConfig` row, edit blob XML, or click "Skip Current Task" — these mutate prod rollout state and require lease-owner approval.

### Step 5 — Summarize and escalate

Post `mitigation_summary` as an ICM discussion (or return it). If the branch concludes "escalate", route to `XStore/Deployment` oncall (Redmond) or `yazzhang` (Shanghai) per [_references.md](_references.md).

## Automation Notes

```
CODING_ABILITY_DEPENDENCY:
  - icm-get-incident (read incident title/description; post discussion comment)
  - dgrep-query (alert-keyword log retrieval, Step 2)
  - storage-account-tenant-metadata (resolve home tenant for XDS lookups in branches)
  - xds-api-call (role ping, smoke history checks for CheckRolePing*/MonitorUpgradeBatchProgress/SmokeTest branches — read-only)
  - GAP: no coding ability for reading/writing Azure Storage blobs by name (xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/<operation> XML)
  - GAP: no coding ability for Azure Table writes against DynamicSettingConfig (and write is intentionally manual-only)
  - GAP: no coding ability for "XDS UI Skip Current Task" (UI-only Advanced Operation)
  - GAP: no coding ability for opening PRs against Azure-Gold-Config / Storage-XKulfi (ValidateRolloutEntityOperation branch)

TSG_CALL: none (all branches are inline step files; no calls to other TsgBase classes)

AUTOMATABLE: Partially.
  - Steps 1, 2, 3, 5 are fully automatable (parsing, DGrep, routing, ICM comment).
  - Branch logic in Step 4 is read-only triage + evidence package; the actual mitigation
    (DynamicSettingConfig insert, blob XML edit, "Skip Current Task" UI click, repo PR)
    is mandated to stay manual because it mutates live rollout state and requires
    lease-owner approval per the source TSGs.

MANUAL_FALLBACK: If automation cannot parse the incident title (unknown format) or
DGrep returns no rows for the keyword, fall back to step-4z (generic escalation):
post the raw title + DGrep link + storage blob path to ICM and page XStore/Deployment
oncall.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is there an existing coding ability (or sanctioned API) to read XML from `xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/<operation>` so Step 2 / step-4i can ingest history without manual blob-explorer access? |
| 2 | Is there a programmatic way to inspect the XDS "Upgrade State" / "Skip Current Task" pane (read-only) so step-4a (PrepareBatch) can report the current task name without screenshotting `Troubleshooting information`? |
| 3 | The incident title for the older format `[<Operation>=<DeploymentId>]` does not include `UpgradeDomain` or target version. Should the parser flag those fields as `None` and continue, or refuse to route and escalate? Source docs are silent. |
| 4 | `ApplicableToApServiceRollout` defaults to `false`. Does that mean the per-operation skip (e.g., `RetryCountBeforeSkip | ApServiceRollout`) is silently ignored, or does it block the rollout type entirely? Behavior matters for ValidateRolloutEntityOperation which fires under `ApServiceRollout`. |
| 5 | For ZRS tenants the source mentions a "virtual tenant" used as the blob folder name. How is that virtual tenant resolved from the physical tenant in the incident title? `storage-account-tenant-metadata` may cover this — needs verification. |
| 6 | Source repeatedly references `DynamicConfigSetting` and `DynamicSettingConfig` — is the table actually named `DynamicSettingConfig` (per the index)? Confirm before any future write automation. |
