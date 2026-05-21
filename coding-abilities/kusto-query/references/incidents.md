# Incident-related KQL patterns

These examples are **sanitized templates** intended to be copy/pasted and adapted.

Verified cluster/database (schema checked via `getschema` on 2026-03-05):

- Cluster: `https://icmcluster.kusto.windows.net`
- Database: `IcmDataWarehouse`

Schema highlights (subset)

- `Incidents`
    - `IncidentId: long`, `CreateDate: datetime`, `ModifiedDate: datetime`
    - `Severity: int`, `Status: string`, `Title: string`
    - `OwningTenantName: string`, `OwningTeamName: string`
    - `CorrelationId: string`, `RoutingId: string`, `Lens_IngestionTime: datetime`, `MitigateDate: datetime`
- `IncidentCustomFieldEntries`
    - `IncidentId: long`, `CustomFieldId: long`, `Value: string`, `ModifiedDate: datetime`, `Lens_IngestionTime: datetime`

- Replace placeholders like `<service>`, `<team_list>`, `<lookbackDays>`, `<N>`.
- Keep queries time-bounded and add `take` when exploring.

## Example: Recent incidents (dedup by IncidentId)

```kusto
cluster('icmcluster').database('IcmDataWarehouse').Incidents
| where CreateDate > ago(<lookbackDays>d)
| where OwningTenantName =~ '<service>'
| summarize arg_max(ModifiedDate, *) by IncidentId
| project IncidentId, CreateDate, ModifiedDate, Status, Severity, Title, OwningTeamName, OwningTenantName
| order by CreateDate desc
| take <N>
```

Sample result (queried 2026-03-05, `OwningTenantName = 'Xstore'`, `lookbackDays = 7`, `take 3`):

| IncidentId | CreateDate | Status | Severity | Title | OwningTeamName |
|---|---|---|---|---|---|
| 757115551 | 2026-03-05T03:16:24Z | ACTIVE | 4 | Long lasting migration with state Dst_MigrateComplete on MS-DUB13PrdStr03A (1 year) | XSTORE\\XStoreWhatIf |
| 757115546 | 2026-03-05T03:16:23Z | ACTIVE | 3 | Monitor PushEngine_Init_Workflow_Error fired on MS-BLZ22PrdSte27G | XSTORE\\TestTriage |
| 757115545 | 2026-03-05T03:16:23Z | ACTIVE | 4 | AsyncCopyBlobFailure - ActualErrorCode: MS-PHX10PrdStp03A 200 0x830a0480 | XSTORE\\PageBlobAndDisks |

Inspired by:
- jupyter-templates/Xstore/FE/GeneralIncidentEnrichment/RepeatOffenderEnrichment.ipynb

## Example: Active incidents joined with a custom field table

```kusto
let IncidentsScoped =
    cluster('icmcluster').database('IcmDataWarehouse').Incidents
    | where Lens_IngestionTime >= ago(<lookbackDays>d)
    | summarize arg_max(Lens_IngestionTime, *) by IncidentId
    | where OwningTeamName in~ (<team_list>)
    | where isnull(MitigateDate)
    | project IncidentId, CreateDate, ModifiedDate, OwningTeamName, Title, Severity;

IncidentsScoped
| join kind=leftouter (
    cluster('icmcluster').database('IcmDataWarehouse').IncidentCustomFieldEntries
    | where CustomFieldId in (<custom_field_id_list>)
    | summarize arg_max(ModifiedDate, *) by IncidentId
    | project IncidentId, CustomFieldValue = Value
) on IncidentId
| project CreateDate, ModifiedDate, IncidentId, OwningTeamName, Title, Severity, CustomFieldValue
| order by OwningTeamName asc, CreateDate asc
| take <N>
```

Sample result (queried 2026-03-05, `team_list = ("XSTORE\\FE", "XSTORE\\FE(Sev34)")`, `lookbackDays = 7`, `take 3`):

| IncidentId | CreateDate | OwningTeamName | Severity | Title | CustomFieldValue |
|---|---|---|---|---|---|
| 727590186 | 2025-12-28T06:46:11Z | XSTORE\\FE | 3 | Monitor XStore/XFE/FEMissingAccountAccessTier/… raised event for MS-YQ1PrdStr10A | N/A - This incident does not have a support ticket… |
| 727599027 | 2025-12-28T07:29:32Z | XSTORE\\FE | 4 | [TEST_CRASH] [Production] MS-ATL20PrdStr21A Process Nephos.Blob Restarts with unexpected error code 0xc0000005 | N/A - This incident does not have a support ticket… |

Inspired by:
- jupyter-templates/Xstore/FE/STGXX.ipynb
