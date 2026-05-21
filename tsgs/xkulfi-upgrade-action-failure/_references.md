# Shared References — XKulfi UpgradeActionFailure

## Storage account / blob

- **Account**: `xdashxstorepublicpf`
- **Container**: `xkulfi`
- **Per-operation history path**: `TenantStatus/<tenant>/<operation>` (XML file). For ZRS, `<tenant>` is the **virtual tenant** name.
- **Tenant rollout info path**: `TenantStatus/<virtual-tenant>/TenantRolloutInfo` (XML; edited manually in step-4i).

## DynamicSettingConfig table

- **Hosted on**: storage account `xdashxstorepublicpf`
- **Schema**:

| Column | Description |
|---|---|
| `PartitionKey` | Tenant name |
| `RowKey` | `<Operation>.<Config> \| <RolloutType> [\| <Domain>]?` |
| `DeploymentId` | Group rollout id (e.g., `01DA3D2E5D725E70:1943`) |
| `Value` | Knob value (int / bool / xml) |
| `UpdatedBy` | Alias of the engineer making the change |
| `ValidBefore` | Optional expiry timestamp |

## Default config knob values

| Knob | Default |
|---|---|
| `TimeoutInSeconds` | 900 |
| `RetryCountBeforeAlert` | 3 |
| `RetryCountBeforeSkip` | -1 |
| `RetryBakeTimeInSeconds` | 0 |
| `MitigateIncidentAfterSuccess` | true |
| `MitigateIncidentAfterDelayInSeconds` | 300 |
| `UpgradeActionIncidentSeverity` | 3 |
| `UpgradeActionIncidentKeyword` | `XKulfiAutoAlert` |
| `CaptureBeginEndEvents` | true |
| `CaptureInProgressEvent` | true |
| `ApplicableToApServiceRollout` | false |

## Escalation contacts

| Window | Contact |
|---|---|
| Redmond hours | `XStore/Deployment` oncall (ICM team) |
| Shanghai hours | `yazzhang` (XKulfi Shanghai) |
| `CheckRolesAlterationOperation` (Shanghai) | `liuzhouchen` |
| Owning team id | `XStore/Deployment` (per `UpgradeActionIncidentOwningTeamId`) |

## Useful links

- ConfigurationInstructions (operation knobs): https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/xpfdeployment/xkulfi/operation_document/configurationinstructions
- Trigger manual repair: https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/xpfdeployment/xkulfi/operation_document/triggermanualrepair
- Fabric "Master TSG" (smoke + monitor batch fallback): https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/stgos/incidents/_master_tsg
- How to abort an AppRollout: https://msazure.visualstudio.com/One/_wiki/wikis/XKulfi/160614/AppRollout-manual-actions?anchor=how-to-abort-an-approllout%3F
- XDS UI path for skip-current-task: XDS UI ▸ Tenant Status ▸ Upgrade State ▸ Advanced Operations ▸ "Skip Current Task" (Preprod only, lease-owner approval required)
- XDS UI path for history job results: XDS UI ▸ Tenant Utils ▸ XLock Tool ▸ XDS ▸ `upgradetool` ▸ `upgradecpeevents`

## Sample incidents

| Incident | Operation | Note |
|---|---|---|
| 569195691 | `PrepareBatchOperation` | XDS preparation timeout |
| 455450715 | `ScheduleXComputeJobsOperation` | post-rollout schedule failure |
| 451853863 | `UpdateStgVersionOperation` | post-rollout metadata update |
| 491737669 | `CheckRolePingAfterUnprepareOperation` | 2/23 unresponsive after AppRollout |
| 493282112 | `CheckRolePingBeforeUnprepareOperation` | 17/18 unresponsive |
| 590196527 | `CheckRolesAlterationOperation` | role instances changed |
| 455401851 | `DeploySecretsOperation` | SecretsConfigLibException |
| 486860675 | `MonitorUpgradeBatchProgressOperation` | unhealthy machines |
| 739763565 | `PostPrepareBatchOperation` | KeyNotFoundException, XML edit |
| 489230068 | `SmokeTestOperation` | HealthChecks quorum failing |
| 455672116 | `ValidateBuildOperation` | empty build |
| 701103648 | `ValidateRolloutEntityOperation` | new VE not configured |

## Repo references (for ValidateRolloutEntityOperation)

- `Azure-Gold-Config`: `XStore-Global` VE → `environment.ini` → `Orchestration` section. Sample PR: https://dev.azure.com/azureconfig/Gold/_git/Azure-Gold-Config/pullrequest/941797
- `Storage-XKulfi`: `StorageTenantGroupSettings.xml` → `ValidateRolloutEntityOperation.AllowedDeploymentEntities`. Sample PR: https://msazure.visualstudio.com/One/_git/Storage-XKulfi/pullrequest/13841810
