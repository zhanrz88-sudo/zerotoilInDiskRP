# Generic KQL patterns (joins, binning, arg_max)

These examples are **sanitized templates** that show common KQL shapes.

Note: For real execution, the `cluster` + `database` pair must be chosen so the referenced tables/functions actually exist. The cluster/database pairs shown below are common ones used in `jupyter-templates/`.

## Example: Time-bucket join across two datasets

```kusto
let startTime = ago(<hours>h);

let left =
    cluster('xdeployment.westcentralus.kusto.windows.net').database('Deployment').<LeftTable>
    | where Timestamp > startTime
    | project Key = tolower(<key_expr>), Timestamp, LeftValue = <left_value_expr>
    | extend bucket = bin(Timestamp, 1h);

let right =
    cluster('icmcluster.kusto.windows.net').database('IcmDataWarehouse').<RightTable>
    | where Timestamp > startTime
    | project Key = tolower(<key_expr>), Timestamp, RightValue = <right_value_expr>
    | extend bucket = bin(Timestamp, 1h);

left
| join kind=inner right on Key
| where bucket == bucket1 or bucket == bucket1 - 1h
| project Timestamp, Key, LeftValue, RightValue
| order by Timestamp desc
| take <N>
```

Sample result (queried 2026-03-05, concrete tables: `DynamicConfigChangedEvent` join `Incidents`, `hours = 3`, `take 3`):

| Timestamp | Key | SettingName | UserName | IncidentId | Title | Severity |
|---|---|---|---|---|---|---|
| 2026-03-05T02:57:48Z | ms-bnz14prdstr08a | XStoreConfigSettings.XConfigGoalStateSettings.GeneratedAt | upgrade.store.core.windows.net-subjectName | 757090660 | Continous HPA on MS-BNZ14PrdStr08A for CSM | 2 |
| 2026-03-05T02:57:48Z | ms-bnz14prdstr08a | XStoreConfigSettings.XcfgFastVersion | upgrade.store.core.windows.net-subjectName | 757090660 | Continous HPA on MS-BNZ14PrdStr08A for CSM | 2 |

Inspired by:
- jupyter-templates/Xstore/XTable/GC/GCReport/TrackingIcmCausedByDCChange.ipynb

## Example: Deduplicate a stream using `arg_max`

```kusto
<MyTable>
| where Timestamp > ago(<hours>h)
| summarize arg_max(Timestamp, *) by <entity_id_column>
| project <entity_id_column>, Timestamp, <important_columns>
| take <N>
```

Sample result (queried 2026-03-05, `Incidents | arg_max(ModifiedDate, *) by IncidentId`, `take 3`):

| IncidentId | ModifiedDate | Status | Severity | Title |
|---|---|---|---|---|
| 21000000932410 | 2026-03-05T03:07:08Z | ACTIVE | 4 | USSec HS IcM #8558607 |
| 21000000932488 | 2026-03-05T03:07:14Z | ACTIVE | 4 | USNat HS IcM #13338761 |
| 21000000932504 | 2026-03-05T03:10:15Z | ACTIVE | 4 | Unable to establish a connection to Myworkspace |

Inspired by:
- jupyter-templates/Xstore/FE/GeneralIncidentEnrichment/RepeatOffenderEnrichment.ipynb
- jupyter-templates/Xstore/FE/STGXX.ipynb
