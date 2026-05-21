# Deployment / rollout KQL patterns

These examples are **sanitized templates**.

Verified cluster/databases (schema checked via `getschema` on 2026-03-05):

- Deployments: `https://xdeployment.westcentralus.kusto.windows.net` / `Deployment`
- Action events: `https://xstore.kusto.windows.net` / `xlivesite`

Schema highlights (subset)

- `AllDeploymentsFromReleaseDS`
    - `StartDate: datetime`, `FinishDate: datetime`, `ChangedDate: datetime`
    - `TenantName: string`, `Component: string`, `TemplateName: string`
    - `DeploymentEngineId: string`, `BuildNumber: string`, `ComponentVersion: string`
- `UpgradeActionEvent`
    - `time: datetime`, `action: string`, `state: string`, `status: string`
    - `durationInSecond: real`, `deploymentID: string`, `innerAction1: string`
- `DynamicConfigChangedEvent`
    - `env_time: datetime`, `env_cloud_name: string`
    - `SettingName: string`, `SettingCurrentValue: string`, `SettingPreviousValue: string`, `UserName: string`

- Replace placeholders like `<fromTime>`, `<component>`, `<template>`, `<N>`.
- Prefer keeping joins scoped to a reasonable time window.

## Example: Deployment list joined with action/telemetry events

```kusto
let startTime = ago(<lookbackDays>d);

let deployments =
    cluster('xdeployment.westcentralus.kusto.windows.net').database('Deployment').AllDeploymentsFromReleaseDS
    | where StartDate > startTime
    | where Component == '<component>' and TemplateName == '<template>'
    | project TenantName, BuildNumber, StartDate, DeploymentEngineId;

let actions =
    cluster('xstore.kusto.windows.net').database('xlivesite').UpgradeActionEvent
    | where ['time'] > startTime
    | where action == '<action>' and state == 'Ended' and status == 'Success'
    | summarize ActionDurationSeconds = max(durationInSecond), ActionTime = min(['time']) by deploymentID
    | project DeploymentEngineId = deploymentID, ActionDurationMinutes = round(ActionDurationSeconds / 60.0), ActionTime;

deployments
| join kind=inner actions on DeploymentEngineId
| project StartDate, TenantName, BuildNumber, DeploymentEngineId, ActionTime, ActionDurationMinutes
| order by StartDate desc
| take <N>
```

Sample result (queried 2026-03-05, `Component = 'STG'`, `TemplateName = 'STG_UpdateWithoutHE.xml'`, `action = 'addimage'`, `lookbackDays = 7`, `take 3`):

| StartDate | TenantName | BuildNumber | DeploymentEngineId | ActionTime | ActionDurationMinutes |
|---|---|---|---|---|---|
| 2026-03-05T00:06:20Z | MS-TYO60PrdStr02A | 103.334.220.2300 | 1d77856d-673d-4f70-93de-1deb1db09184 | 2026-03-05T00:13:06Z | 1.0 |
| 2026-03-04T23:34:40Z | MS-BLZ21PrdStf03A | 103.334.468.500 | bc0c5f60-820a-414e-a1e8-979bf3b0b2c8 | 2026-03-05T00:30:49Z | 32.0 |
| 2026-03-04T22:40:09Z | MS-BL5PrdStr20A | 103.334.468.500 | 31ab7e4f-db95-4475-a5f8-4feb4990e1a9 | 2026-03-04T23:28:37Z | 38.0 |

Inspired by:
- jupyter-templates/Xstore/XDeployment/WeeklyAddImageEmailReport.ipynb

## Example: Dynamic config changes in a time window

```kusto
DynamicConfigChangedEvent
| where env_time between (ago(<hours>h) .. now())
| where SettingName !contains 'LastUpdatedBy' and SettingName !contains 'VersionIdentifier'
| where SettingCurrentValue != SettingPreviousValue
| project env_time, TenantName = tolower(env_cloud_name), SettingName, SettingCurrentValue, SettingPreviousValue, UserName
| order by env_time desc
| take <N>
```

Sample result (queried 2026-03-05, `hours = 1`, `take 3`):

| env_time | TenantName | SettingName | SettingCurrentValue | SettingPreviousValue | UserName |
|---|---|---|---|---|---|
| 2026-03-05T03:08:42Z | ms-par60prdstr01b | XStoreConfigSettings.CsmSettings.EnableRslExtentCreationManager | true | false | upgrade.store.core.windows.net-subjectName |
| 2026-03-05T03:08:42Z | ms-par60prdstr01b | XStoreConfigSettings.CsmSettings.EnableInlineEcPolicy | true | false | upgrade.store.core.windows.net-subjectName |
| 2026-03-05T03:08:42Z | ms-par60prdstr01b | XStoreConfigSettings.CsmSettings.EnableSyncRefactor | true | false | upgrade.store.core.windows.net-subjectName |

Inspired by:
- jupyter-templates/Xstore/XTable/GC/GCReport/TrackingIcmCausedByDCChange.ipynb
