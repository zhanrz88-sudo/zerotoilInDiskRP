# Infra / capacity / health KQL patterns

These examples are **sanitized templates**.

Verified cluster/databases (schema checked via `getschema` on 2026-03-05):

- Infra properties: `https://apdmdata.kusto.windows.net` / `DeviceManager`
- ICM incidents (for correlation): `https://icmcluster.kusto.windows.net` / `IcmDataWarehouse`
- Test execution: `https://sibyl.centralus.kusto.windows.net` / `Storage-XStore`

Schema highlights (subset)

- `Env_AllMachineProperties`
    - `AutoGen_TimeStamp: datetime`, `AutoGen_Environment: string`
    - `machineName: string`, `property: string`, `value: string`
- `Incidents`
    - `CorrelationId: string`, `Status: string`

- Replace placeholders like `<thresholdMb>`, `<lookbackDays>`, `<N>`.
- Keep time filters tight when starting.

## Example: Low disk space candidates + exclude already-active incidents

```kusto
let thresholdMb = <thresholdMb>;

let lowDisk =
    cluster('apdmdata.kusto.windows.net').database('DeviceManager').Env_AllMachineProperties
    | where AutoGen_TimeStamp > ago(<lookbackDays>d)
    | where property == 'diskusage'
    // Example parsing pattern; adjust to the actual payload format
    | extend free_mb = toint(extract(@"(\\d+)\\s*MBytes free", 1, tostring(value)))
    | summarize min_free_mb = min(free_mb) by Environment = AutoGen_Environment
    | where min_free_mb < thresholdMb
    | extend CorrelationId = strcat('LowDiskSpace-', Environment);

lowDisk
| join kind=leftanti (
    cluster('icmcluster').database('IcmDataWarehouse').Incidents
    | where Status == 'ACTIVE'
    | where CorrelationId startswith 'LowDiskSpace-'
    | project CorrelationId
) on CorrelationId
| project Environment, min_free_mb
| order by min_free_mb asc
| take <N>
```

Sample result (queried 2026-03-05, `thresholdMb = 50000`, `lookbackDays = 2`, `take 3`):

| Environment | min_free_mb |
|---|---|
| BY3PrdApp07-AzNodes-Prod-BY01P | 0 |
| WacProductionFIL1-Prod-TLV03P | 0 |
| AMS06PrdStr12-AzNodes-Prod-AMS02P | 0 |

Inspired by:
- jupyter-templates/Xstore/XDeployment/LowDiskSpaceAlert.ipynb

## Example: Pipeline/test failures in a time window

```kusto
let end_time = now();
let start_time = end_time - timespan(<hours>h);

TestExecution
| where StartTime between (start_time .. end_time)
| where CtJobName contains '<job_name_hint>'
| where TestCategory == '<category>'
| where BaseTestName contains '<test_name_hint>'
| where BranchName == '<branch>'
| where TestResult == 'Failed'
| project StartTime, CtJobName, PipelineBuildId
| order by StartTime desc
| take <N>
```

Cluster/database: `https://sibyl.centralus.kusto.windows.net` / `Storage-XStore`

Sample result (queried 2026-03-05, `hours = 12`, `take 3`):

| StartTime | CtJobName | PipelineBuildId | TestCategory | BaseTestName | BranchName |
|---|---|---|---|---|---|
| 2026-03-05T02:54:51Z | Coverage_CIT_amd64_NFSv3FE_024 | 155483544 | | Nfsv3::PacketLevelTests::NfsV3DRCBasicTest[Class_Setup] | main |
| 2026-03-05T02:57:50Z | Coverage_CIT_amd64_NFSv3FE_024 | 155483544 | | Nfsv3::PacketLevelTests::NfsV3ProcWRITETest[Class_Setup] | main |
| 2026-03-05T02:35:51Z | Coverage_CIT_amd64_NFSv3FE_024 | 155483544 | Infra | __.MainWorker | main |

Inspired by:
- jupyter-templates/Xstore/XFundamental/XFunSloMonitor/ArmadaDFStatusMonitor.ipynb
