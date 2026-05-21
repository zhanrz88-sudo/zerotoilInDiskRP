# Sample Incidents — XKulfi Upgrade Action Failure

This file stores sample incident titles used to validate and refine the
`XKulfiUpgradeActionFailure` TSG automation. Incidents listed here are the
canonical fixtures for dry-run validation, parsing tests, and regression
checks.

> **Discovery note:** This file is referenced by the TSG code-writer and
> unit-test workflows. Keep the section headers, table columns, and
> `<!-- BEGIN/END: SAMPLE_INCIDENTS -->` markers stable so sample
> incidents can be parsed/discovered programmatically later.

## Title format

Each XKulfi `UpgradeActionFailure` alert title follows this shape:

```text
[XKulfi] [<Region>] [XStore] <Cluster> Alert: UpgradeActionFailure
  [Tenant=<Tenant>]
  [RepairKind=<Kind>]
  [Version=<Version>]
  [OperationName=<Operation>]
  [ActionKey=<...>]
```

The table below lifts the parsed fields out of each title. Add the
incident ID once you have it — the `Incident ID` column is intentionally
left blank for entries that were collected from titles only.

## How to add a sample

1. Append a row to the table inside the `SAMPLE_INCIDENTS` markers.
2. Fill in the `Incident ID` once known. Use placeholders (no PII) in
   `Notes`.
3. If the title is unusual, add the raw title to the
   [Raw titles (reference)](#raw-titles-reference) section at the bottom.

## Sample incidents

<!-- BEGIN: SAMPLE_INCIDENTS -->

| # | Incident ID | Region | Cluster | Tenant | RepairKind | Version | OperationName | Notes |
|---|-------------|--------|---------|--------|------------|---------|---------------|-------|
| 1  |  | Central US EUAP   | MS-CDM40PrdSty02A   | MS-CDM40PrdSty02A | AppRollout         | UnknownSTGVersion                                                                | ValidateBuildOperation                      |  |
| 2  |  | Australia East    | MS-SYD27PrdStp06A   | MS-SYD27PrdStp06A | OSUpgrade          | 26.02.06W2022.XSTORE                                                             | MonitorUpgradeBatchProgressOperation        |  |
| 3  |  | East US 2 EUAP    | MS-BNZ02PrdStp100A  | MS-BNZ02PrdStp100A | OSUpgrade         | 26.03.27W2022.XSTORE                                                             | MonitorUpgradeBatchProgressOperation        |  |
| 4  |  | North Europe      | MS-DUB14PrdStr46A   | MS-DUB14PrdStr46A | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | CheckRolePingBeforeUnprepareOperation       |  |
| 5  |  | East US           | MS-IAD04PrdStp02A   | MS-IAD04PrdStp02A | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | CheckRolePingBeforeUnprepareOperation       |  |
| 6  |  | Australia East    | MS-SYD02PrdStf101A  | MS-SYD02PrdStf101A | OSUpgrade         | 26.03.27W2022.XSTORE                                                             | MonitorUpgradeBatchProgressOperation        |  |
| 7  |  | East US 2 EUAP    | MS-CVL01PrdStf01C   | MS-CVL01PrdStf01C | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | SmokeTestOperation                          |  |
| 8  |  | East US 2 EUAP    | MS-CVL01PrdStf01C   | MS-CVL01PrdStf01C | ApServiceRollout   | AP_2026_04_13_12003                                                              | SmokeTestOperation                          |  |
| 9  |  | East US           | MS-BLZ21PrdStrz27A  | MS-BLZ21PrdStr27A | ApServiceRollout   | AP_2026_04_06_5003                                                               | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 10 |  | West US 2         | MS-EAT03PrdStfz01A  | MS-MWH01PrdStf01A | AppRollout         | RELEASE_STG103/103.334.627.0                                                     | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 11 |  | North Central US  | MS-CHI05PrdStrz15A  | MS-CHI05PrdStr15A | ApServiceRollout   | AP_2026_04_06_5003                                                               | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 12 |  | East US 2 EUAP    | MS-CVL01PrdStf01C   | MS-CVL01PrdStf01C | AppRollout         | RELEASE_STG104_224/104.467.224.600                                               | CheckRolePingAfterUnprepareOperation        |  |
| 13 |  | East US 2 EUAP    | MS-CBN10PrdStfz03A  | MS-CVL01PrdStf01A | AppRollout         | RELEASE_STG104_224/104.467.224.400                                               | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 14 |  | South Central US  | MS-SAT15PrdSte01E   | MS-SAT15PrdSte01E | AppRollout         | UnknownSTGVersion                                                                | ValidateBuildOperation                      |  |
| 15 |  | South Central US  | MS-SAT15PrdSte01C   | MS-SAT15PrdSte01C | AppRollout         | UnknownSTGVersion                                                                | ValidateBuildOperation                      |  |
| 16 |  | West US           | MS-SJC04PrdSte100A  | MS-SJC04PrdSte100A | AppRollout        | RELEASE_STG104_224/104.467.224.600                                               | SmokeTestOperation                          |  |
| 17 |  | West Europe       | MS-AMS26PrdStr14B   | MS-AMS26PrdStr14B | AppRollout         | RELEASE_STG103_468/103.334.468.1000                                              | TenantHealthSignOffOperation                |  |
| 18 |  | West US           | MS-DSM09PrdSty01F   | MS-DSM09PrdSty01F | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | CheckRolePingBeforeUnprepareOperation       |  |
| 19 |  | East US           | MS-BLZ04PrdStez100A | MS-MNZ09PrdSte100A | OSUpgrade         | 26.04.13W2022.XSTORE                                                             | CheckRolePingAfterUnprepareOperation        | Cluster vs Tenant name differ |
| 20 |  | West Europe       | MS-AMS26PrdStr14B   | MS-AMS26PrdStr14B | AppRollout         | RELEASE_STG103_468/103.334.468.1000                                              | CheckLeftOverMachinesBeforeUnbookOperation  |  |
| 21 |  | North Europe      | MS-DB5PrdStrz15A    | MS-DB5PrdStr15A   | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | MonitorUpgradeBatchProgressOperation        | Cluster vs Tenant name differ |
| 22 |  | East US 2 EUAP    | MS-CBN49PrdStf01C   | MS-CBN49PrdStf01C | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | MonitorUpgradeBatchProgressOperation        |  |
| 23 |  | East US 2 EUAP    | MS-CBN10PrdStfz03A  | MS-CVL01PrdStf01A | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 24 |  | East US           | MS-MWH01PrdStev11A  | MS-MWH01PrdStev11A | AppRollout        | RELEASE_STG104/104.467.224.0                                                     | CheckLeftOverMachinesBeforeUnbookOperation  |  |
| 25 |  | East US 2 EUAP    | MS-CBN03PrdStp100A  | MS-CBN03PrdStp100A | AppRollout        | RELEASE_STG104_224/104.467.224.400                                               | SmokeTestOperation                          | Title note: needs updated build with logging fix |
| 26 |  | East US           | MS-BLZ21PrdStrz27A  | MS-BLZ21PrdStr27A | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 27 |  | North Central US  | MS-CHI05PrdStrz15A  | MS-CHI26PrdStr16A | ApServiceRollout   | AP_2026_03_30_29003                                                              | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 28 |  | East US           | MS-IAD04PrdStrz38A  | MS-MNZ22PrdStr27A | AppRollout         | RELEASE_STG103/103.334.627.0                                                     | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 29 |  | East US           | MS-BLZ21PrdStrz27A  | MS-BLZ21PrdStr27A | ApServiceRollout   | AP_2026_03_30_29003                                                              | SmokeTestOperation                          | Cluster vs Tenant name differ |
| 30 |  | West Central US   | MS-CYS42PrdStr05B   | MS-CYS42PrdStr05B | AppRollout         | UnknownSTGVersion                                                                | ValidateBuildOperation                      |  |
| 31 |  | West US           | MS-DM3PrdStez13A    | MS-DSM14PrdSte28A | AppRollout         | RELEASE_STG103_577/103.334.577.100                                               | UpdateConfigurationStorageVersionOperation  | Same ActionKey as 32–34 |
| 32 |  | West US           | MS-DM3PrdStez13A    | MS-DSM14PrdSte28A | AppRollout         | RELEASE_STG103_577/103.334.577.100                                               | ScheduleXComputeJobsOperation               | Same ActionKey as 31, 33, 34 |
| 33 |  | West US           | MS-DM3PrdStez13A    | MS-DSM14PrdSte28A | AppRollout         | RELEASE_STG103_577/103.334.577.100                                               | UpdateStgVersionOperation                   | Same ActionKey as 31, 32, 34 |
| 34 |  | West US           | MS-DM3PrdStez13A    | MS-DSM14PrdSte28A | AppRollout         | RELEASE_STG103_577/103.334.577.100                                               | ResetWatchdogConfigOperation                | Same ActionKey as 31–33 |
| 35 |  | West US           | MS-DSM09PrdSte11C   | MS-DSM09PrdSte11C | AppRollout         | RELEASE_STG103_468/103.334.468.500                                               | UpdateConfigurationStorageVersionOperation  |  |
| 36 |  | Central US        | MS-DSM41PrdStr13B   | MS-DSM41PrdStr13B | OSUpgrade          | 26.03.27W2022.XSTORE                                                             | CheckRolePingBeforeUnprepareOperation       |  |
| 37 |  | West US           | MS-PHX25PrdStr38A   | MS-PHX25PrdStr38A | FeatureFlagsUpgrade | DotNetCore_8.0.24_26.2.12002.0.DotNetCore_8.0.25_26.3.13002.0.FeatureFlags      | CheckRolePingBeforeUnprepareOperation       | Title truncated in source |
| 38 |  | East US 2 EUAP    | MS-BNZ02PrdStp100A  | MS-BNZ02PrdStp100A | OSUpgrade         | 26.03.27W2022.XSTORE                                                             | MonitorUpgradeBatchProgressOperation        |  |
| 39 |  | East US 2 EUAP    | MS-CBN10PrdStfz03A  | MS-CVL01PrdStf01A | AppRollout         | RELEASE_STG104_224/104.467.224.400                                               | SmokeTestOperation                          | Cluster vs Tenant name differ; ActionKey lacks UpgradeDomain |
| 40 |  | West US 2         | MS-EAT03PrdStfz01A  | MS-MWH06PrdStf01A | ApServiceRollout   | AP_2026_04_06_5003                                                               | SmokeTestOperation                          | Cluster vs Tenant name differ |

<!-- END: SAMPLE_INCIDENTS -->

## Observations

- `RepairKind` values seen: `AppRollout`, `OSUpgrade`, `ApServiceRollout`, `FeatureFlagsUpgrade`.
- `OperationName` values seen: `ValidateBuildOperation`, `MonitorUpgradeBatchProgressOperation`,
  `CheckRolePingBeforeUnprepareOperation`, `CheckRolePingAfterUnprepareOperation`,
  `SmokeTestOperation`, `TenantHealthSignOffOperation`,
  `CheckLeftOverMachinesBeforeUnbookOperation`, `UpdateConfigurationStorageVersionOperation`,
  `ScheduleXComputeJobsOperation`, `UpdateStgVersionOperation`, `ResetWatchdogConfigOperation`.
- Several titles have a **Cluster** identifier in the title prefix that
  differs from the **Tenant** value inside the `[Tenant=...]` segment
  (rows flagged in the `Notes` column). The TSG parser must rely on the
  `[Tenant=...]` segment, not the title prefix.
- `Version=UnknownSTGVersion` appears for `ValidateBuildOperation`
  failures.
- Rows 31–34 share an ActionKey and only differ by `OperationName` —
  useful as a deduplication / grouping fixture.
- Row 39's ActionKey omits the `[UpgradeDomain=N]` segment that other
  AppRollout entries include — a parsing edge case.

## Raw titles (reference)

Original titles as captured (one per line). Preserve order to match the
`#` column above.

<!-- BEGIN: RAW_TITLES -->

```text
[XKulfi] [Central US EUAP] [XStore] MS-CDM40PrdSty02A Alert: UpgradeActionFailure [Tenant=MS-CDM40PrdSty02A] [RepairKind=AppRollout][Version=UnknownSTGVersion][OperationName=ValidateBuildOperation][ActionKey=MS-CDM40PrdSty02A;01DCCB8A7C608163:3160;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;UnknownSTGVersion]
[XKulfi] [Australia East] [XStore] MS-SYD27PrdStp06A Alert: UpgradeActionFailure [Tenant=MS-SYD27PrdStp06A] [RepairKind=OSUpgrade][Version=26.02.06W2022.XSTORE][OperationName=MonitorUpgradeBatchProgressOperation][ActionKey=[[XKulfi]MS-SYD27PrdStp06A-OSUpgrade-26.02.06W2022.XSTORE][MaintenanceService2][26.02.06W2022.XSTORE][UpgradeDomain=6][2026-04-14T16:59:40Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-BNZ02PrdStp100A Alert: UpgradeActionFailure [Tenant=MS-BNZ02PrdStp100A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=MonitorUpgradeBatchProgressOperation][ActionKey=[[XKulfi]MS-BNZ02PrdStp100A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=1][2026-04-14T21:11:51Z]]
[XKulfi] [North Europe] [XStore] MS-DUB14PrdStr46A Alert: UpgradeActionFailure [Tenant=MS-DUB14PrdStr46A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=CheckRolePingBeforeUnprepareOperation][ActionKey=[[XKulfi]MS-DUB14PrdStr46A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=6][2026-04-15T04:10:41Z]]
[XKulfi] [East US] [XStore] MS-IAD04PrdStp02A Alert: UpgradeActionFailure [Tenant=MS-IAD04PrdStp02A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=CheckRolePingBeforeUnprepareOperation][ActionKey=[[XKulfi]MS-IAD04PrdStp02A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=6][2026-04-15T03:49:14Z]]
[XKulfi] [Australia East] [XStore] MS-SYD02PrdStf101A Alert: UpgradeActionFailure [Tenant=MS-SYD02PrdStf101A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=MonitorUpgradeBatchProgressOperation][ActionKey=[[XKulfi]MS-SYD02PrdStf101A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=9][2026-04-15T20:39:58Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CVL01PrdStf01C Alert: UpgradeActionFailure [Tenant=MS-CVL01PrdStf01C] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CVL01PrdStf01C-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=0][2026-04-16T13:00:10Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CVL01PrdStf01C Alert: UpgradeActionFailure [Tenant=MS-CVL01PrdStf01C] [RepairKind=ApServiceRollout][Version=AP_2026_04_13_12003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CVL01PrdStf01C-ApServiceRollout-01DCCDBE7C90BCC0:7286][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_13_12003][UpgradeDomain=1][2026-04-20T21:15:04Z]]
[XKulfi] [East US] [XStore] MS-BLZ21PrdStrz27A Alert: UpgradeActionFailure [Tenant=MS-BLZ21PrdStr27A] [RepairKind=ApServiceRollout][Version=AP_2026_04_06_5003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z]]
[XKulfi] [West US 2] [XStore] MS-EAT03PrdStfz01A Alert: UpgradeActionFailure [Tenant=MS-MWH01PrdStf01A] [RepairKind=AppRollout][Version=RELEASE_STG103/103.334.627.0][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-MWH01PrdStf01A-AppRollout-01DCCC67897E044B:4822][APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE][RELEASE_STG103/103.334.627.0][UpgradeDomain=7][2026-04-22T08:50:45Z]]
[XKulfi] [North Central US] [XStore] MS-CHI05PrdStrz15A Alert: UpgradeActionFailure [Tenant=MS-CHI05PrdStr15A] [RepairKind=ApServiceRollout][Version=AP_2026_04_06_5003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CHI05PrdStr15A-ApServiceRollout-01DCD026DA973DD6:21619][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=5][2026-04-22T19:30:09Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CVL01PrdStf01C Alert: UpgradeActionFailure [Tenant=MS-CVL01PrdStf01C] [RepairKind=AppRollout][Version=RELEASE_STG104_224/104.467.224.600][OperationName=CheckRolePingAfterUnprepareOperation][ActionKey=[[XKulfi]MS-CVL01PrdStf01C-AppRollout-01DCD3736A2E246A:2960][APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE][RELEASE_STG104_224/104.467.224.600][UpgradeDomain=4][2026-04-24T11:04:54Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CBN10PrdStfz03A Alert: UpgradeActionFailure [Tenant=MS-CVL01PrdStf01A] [RepairKind=AppRollout][Version=RELEASE_STG104_224/104.467.224.400][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CVL01PrdStf01A-AppRollout-01DCCD730C60AED1:5717][APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE][RELEASE_STG104_224/104.467.224.400][UpgradeDomain=8][2026-04-27T17:51:33Z]]
[XKulfi] [South Central US] [XStore] MS-SAT15PrdSte01E Alert: UpgradeActionFailure [Tenant=MS-SAT15PrdSte01E] [RepairKind=AppRollout][Version=UnknownSTGVersion][OperationName=ValidateBuildOperation][ActionKey=MS-SAT15PrdSte01E;01DCD23546E7B3DF:9110;APP~SAT15PRDSTE01E-TEST-SAT07P;UnknownSTGVersion]
[XKulfi] [South Central US] [XStore] MS-SAT15PrdSte01C Alert: UpgradeActionFailure [Tenant=MS-SAT15PrdSte01C] [RepairKind=AppRollout][Version=UnknownSTGVersion][OperationName=ValidateBuildOperation][ActionKey=MS-SAT15PrdSte01C;01DCD23AF3335167:7193;APP~SAT15PRDSTE01C-TEST-SAT07P;UnknownSTGVersion]
[XKulfi] [West US] [XStore] MS-SJC04PrdSte100A Alert: UpgradeActionFailure [Tenant=MS-SJC04PrdSte100A] [RepairKind=AppRollout][Version=RELEASE_STG104_224/104.467.224.600][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-SJC04PrdSte100A-AppRollout-01DCD17683FA53DA:8378][APP~CEG_AZURESTORAGE-XSTORE-ENVIRONMENT-PREPROD-VE][RELEASE_STG104_224/104.467.224.600][UpgradeDomain=0][2026-04-23T07:16:45Z]]
[XKulfi] [West Europe] [XStore] MS-AMS26PrdStr14B Alert: UpgradeActionFailure [Tenant=MS-AMS26PrdStr14B] [RepairKind=AppRollout][Version=RELEASE_STG103_468/103.334.468.1000][OperationName=TenantHealthSignOffOperation][ActionKey=MS-AMS26PrdStr14B;01DCB8DABC81090C:26851;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;RELEASE_STG103_468/103.334.468.1000]
[XKulfi] [West US] [XStore] MS-DSM09PrdSty01F Alert: UpgradeActionFailure [Tenant=MS-DSM09PrdSty01F] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=CheckRolePingBeforeUnprepareOperation][ActionKey=[[XKulfi]MS-DSM09PrdSty01F-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=5][2026-04-02T03:51:15Z]]
[XKulfi] [East US] [XStore] MS-BLZ04PrdStez100A Alert: UpgradeActionFailure [Tenant=MS-MNZ09PrdSte100A] [RepairKind=OSUpgrade][Version=26.04.13W2022.XSTORE][OperationName=CheckRolePingAfterUnprepareOperation][ActionKey=[[XKulfi]MS-MNZ09PrdSte100A-OSUpgrade-26.04.13W2022.XSTORE][MaintenanceService2][26.04.13W2022.XSTORE][UpgradeDomain=1][2026-04-20T04:51:39Z]]
[XKulfi] [West Europe] [XStore] MS-AMS26PrdStr14B Alert: UpgradeActionFailure [Tenant=MS-AMS26PrdStr14B] [RepairKind=AppRollout][Version=RELEASE_STG103_468/103.334.468.1000][OperationName=CheckLeftOverMachinesBeforeUnbookOperation][ActionKey=MS-AMS26PrdStr14B;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;01DCB8DABC81090C:26851;1601-01-01T00:00:00Z]
[XKulfi] [North Europe] [XStore] MS-DB5PrdStrz15A Alert: UpgradeActionFailure [Tenant=MS-DB5PrdStr15A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=MonitorUpgradeBatchProgressOperation][ActionKey=[[XKulfi]MS-DB5PrdStr15A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=2][2026-04-16T03:55:09Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CBN49PrdStf01C Alert: UpgradeActionFailure [Tenant=MS-CBN49PrdStf01C] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=MonitorUpgradeBatchProgressOperation][ActionKey=[[XKulfi]MS-CBN49PrdStf01C-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=4][2026-04-16T00:39:12Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CBN10PrdStfz03A Alert: UpgradeActionFailure [Tenant=MS-CVL01PrdStf01A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CVL01PrdStf01A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=1][2026-04-18T21:08:59Z]]
[XKulfi] [East US] [XStore] MS-MWH01PrdStev11A Alert: UpgradeActionFailure [Tenant=MS-MWH01PrdStev11A] [RepairKind=AppRollout][Version=RELEASE_STG104/104.467.224.0][OperationName=CheckLeftOverMachinesBeforeUnbookOperation][ActionKey=MS-MWH01PrdStev11A;APP~CEG_AZURESTORAGE-XSTORE-ENVIRONMENT-PREPROD-VE;01DCC70492B092BC:256047;1601-01-01T00:00:00Z]
[XKulfi] [East US 2 EUAP] [XStore] MS-CBN03PrdStp100A - needs updated build with logging fix - Alert: UpgradeActionFailure [Tenant=MS-CBN03PrdStp100A] [RepairKind=AppRollout][Version=RELEASE_STG104_224/104.467.224.400][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CBN03PrdStp100A-AppRollout-01DCCCA20C2DC83C:7882][APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE][RELEASE_STG104_224/104.467.224.400][UpgradeDomain=0][2026-04-15T07:51:26Z]]
[XKulfi] [East US] [XStore] MS-BLZ21PrdStrz27A Alert: UpgradeActionFailure [Tenant=MS-BLZ21PrdStr27A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-BLZ21PrdStr27A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=7][2026-04-15T09:38:14Z]]
[XKulfi] [North Central US] [XStore] MS-CHI05PrdStrz15A Alert: UpgradeActionFailure [Tenant=MS-CHI26PrdStr16A] [RepairKind=ApServiceRollout][Version=AP_2026_03_30_29003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CHI26PrdStr16A-ApServiceRollout-01DCC830D4D0CB33:2217][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_03_30_29003][UpgradeDomain=4][2026-04-16T01:10:57Z]]
[XKulfi] [East US] [XStore] MS-IAD04PrdStrz38A Alert: UpgradeActionFailure [Tenant=MS-MNZ22PrdStr27A] [RepairKind=AppRollout][Version=RELEASE_STG103/103.334.627.0][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-MNZ22PrdStr27A-AppRollout-01DCCC6976146AEC:18975][APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE][RELEASE_STG103/103.334.627.0][UpgradeDomain=7][2026-04-16T02:57:39Z]]
[XKulfi] [East US] [XStore] MS-BLZ21PrdStrz27A Alert: UpgradeActionFailure [Tenant=MS-BLZ21PrdStr27A] [RepairKind=ApServiceRollout][Version=AP_2026_03_30_29003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCCC242FFA2150:4857][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_03_30_29003][UpgradeDomain=7][2026-04-17T00:24:50Z]]
[XKulfi] [West Central US] [XStore] MS-CYS42PrdStr05B Alert: UpgradeActionFailure [Tenant=MS-CYS42PrdStr05B] [RepairKind=AppRollout][Version=UnknownSTGVersion][OperationName=ValidateBuildOperation][ActionKey=MS-CYS42PrdStr05B;01DCD40437B5366E:3603;APP~CYS42PRDSTR05B-PROD-CYS06P;UnknownSTGVersion]
[XKulfi] [West US] [XStore] MS-DM3PrdStez13A Alert: UpgradeActionFailure [Tenant=MS-DSM14PrdSte28A] [RepairKind=AppRollout][Version=RELEASE_STG103_577/103.334.577.100][OperationName=UpdateConfigurationStorageVersionOperation][ActionKey=MS-DSM14PrdSte28A;01DCC2C1CFF3B717:1911;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;RELEASE_STG103_577/103.334.577.100]
[XKulfi] [West US] [XStore] MS-DM3PrdStez13A Alert: UpgradeActionFailure [Tenant=MS-DSM14PrdSte28A] [RepairKind=AppRollout][Version=RELEASE_STG103_577/103.334.577.100][OperationName=ScheduleXComputeJobsOperation][ActionKey=MS-DSM14PrdSte28A;01DCC2C1CFF3B717:1911;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;RELEASE_STG103_577/103.334.577.100]
[XKulfi] [West US] [XStore] MS-DM3PrdStez13A Alert: UpgradeActionFailure [Tenant=MS-DSM14PrdSte28A] [RepairKind=AppRollout][Version=RELEASE_STG103_577/103.334.577.100][OperationName=UpdateStgVersionOperation][ActionKey=MS-DSM14PrdSte28A;01DCC2C1CFF3B717:1911;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;RELEASE_STG103_577/103.334.577.100]
[XKulfi] [West US] [XStore] MS-DM3PrdStez13A Alert: UpgradeActionFailure [Tenant=MS-DSM14PrdSte28A] [RepairKind=AppRollout][Version=RELEASE_STG103_577/103.334.577.100][OperationName=ResetWatchdogConfigOperation][ActionKey=MS-DSM14PrdSte28A;01DCC2C1CFF3B717:1911;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;RELEASE_STG103_577/103.334.577.100]
[XKulfi] [West US] [XStore] MS-DSM09PrdSte11C Alert: UpgradeActionFailure [Tenant=MS-DSM09PrdSte11C] [RepairKind=AppRollout][Version=RELEASE_STG103_468/103.334.468.500][OperationName=UpdateConfigurationStorageVersionOperation][ActionKey=MS-DSM09PrdSte11C;01DCC2C1D0A496B3:5772;APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE;RELEASE_STG103_468/103.334.468.500]
[XKulfi] [Central US] [XStore] MS-DSM41PrdStr13B Alert: UpgradeActionFailure [Tenant=MS-DSM41PrdStr13B] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=CheckRolePingBeforeUnprepareOperation][ActionKey=[[XKulfi]MS-DSM41PrdStr13B-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=8][2026-04-13T04:49:08Z]]
[XKulfi] [West US] [XStore] MS-PHX25PrdStr38A Alert: UpgradeActionFailure [Tenant=MS-PHX25PrdStr38A] [RepairKind=FeatureFlagsUpgrade][Version=DotNetCore_8.0.24_26.2.12002.0.DotNetCore_8.0.25_26.3.13002.0.FeatureFlags][OperationName=CheckRolePingBeforeUnprepareOperation][ActionKey=[[XKulfi]MS-PHX25PrdStr38A-FeatureFlagsUpgrade-DotNetCore_8.0.24_26.2.12002.0.DotNetCore_8.0.25_26.3.13002.0.FeatureFlags][MaintenanceService2][DotNetCore_8.0.24_26.2.12002.0.DotNetCore_8.0.25_26.3.13002.0.FeatureFlags][UpgradeDoma
[XKulfi] [East US 2 EUAP] [XStore] MS-BNZ02PrdStp100A Alert: UpgradeActionFailure [Tenant=MS-BNZ02PrdStp100A] [RepairKind=OSUpgrade][Version=26.03.27W2022.XSTORE][OperationName=MonitorUpgradeBatchProgressOperation][ActionKey=[[XKulfi]MS-BNZ02PrdStp100A-OSUpgrade-26.03.27W2022.XSTORE][MaintenanceService2][26.03.27W2022.XSTORE][UpgradeDomain=2][2026-04-17T05:06:45Z]]
[XKulfi] [East US 2 EUAP] [XStore] MS-CBN10PrdStfz03A Alert: UpgradeActionFailure [Tenant=MS-CVL01PrdStf01A] [RepairKind=AppRollout][Version=RELEASE_STG104_224/104.467.224.400][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-CVL01PrdStf01A-AppRollout-01DCCD730C60AED1:5717][APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE][RELEASE_STG104_224/104.467.224.400][2026-04-21T14:42:18Z]]
[XKulfi] [West US 2] [XStore] MS-EAT03PrdStfz01A Alert: UpgradeActionFailure [Tenant=MS-MWH06PrdStf01A] [RepairKind=ApServiceRollout][Version=AP_2026_04_06_5003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-MWH06PrdStf01A-ApServiceRollout-01DCD1D815CE0BF4:10219][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=2][2026-04-23T04:08:00Z]]
```

<!-- END: RAW_TITLES -->

## Related assets

- TSG code: [zerotoil/tsgs/xkulfi_upgrade_action_failure.py](../../zerotoil/tsgs/xkulfi_upgrade_action_failure.py)
- TSG doc: [README.md](README.md)
- Unit tests: [zero-toil/tests](../../tests)
