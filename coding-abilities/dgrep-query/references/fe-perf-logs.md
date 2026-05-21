# FE performance / request failure DGrep patterns

These examples query front-end request logs to investigate availability drops and failed requests.

Namespace: `Xstore`
Events: `NativeFePerfMetric`, `FrontEndSummaryPerfLogs`

## Example: Failed FE requests for a storage account (MQL)

```python
from xportal import dgrep
from xstore.common.dgrep import get_moniker_by_xstore_tenant
import datetime

tenant_name = "<tenant_name>"   # e.g. "MS-AM5PrdStr04A"
account = "<account_name>"      # e.g. "mystorageaccount"

moniker = await get_moniker_by_xstore_tenant(tenant_name)
scope_conditions = {"Moniker": moniker}

namespace = "Xstore"
event_names = ["NativeFePerfMetric", "FrontEndSummaryPerfLogs"]

# MQL query — .Contains() / select syntax
query = f'''where Status != "SASExpectedSuccess" and Status != "ExpectedSuccess" and Status != "Success" and MeasurementStatus != "ExpectedFailure" and (HttpStatusCode < 400 or HttpStatusCode > 499 or HttpStatusCode == 409) and InternalStatus ~= "\\w*(ServerTimeoutError|ServerOtherError|UnexpectedAuthenticationTimeoutError|SASServerPartitionRequestThrottlingError)" and Account == "{account}"'''

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=5)

result = await dgrep.query(
    namespace, event_names, start_time, end_time,
    server_query=query,
    scope_conditions=scope_conditions,
)

df = result.to_df()
result.show()
```

Inspired by:
- jupyter-templates/Xstore/XInvestigator/AccountAvailibilityDiagnostic.ipynb
- jupyter-templates/Xstore/XInvestigator/AccountAvailbilityLow.ipynb

## Example: Failed FE requests (KQL mode)

```python
kql_query = """
source
| where Status != "Success" and Status != "ExpectedSuccess"
| where HttpStatusCode >= 500
| project Account, Status, HttpStatusCode, InternalStatus, PreciseTimeStamp
| take 50
""".strip()

result = await dgrep.query(
    "Xstore", "NativeFePerfMetric", start_time, end_time,
    server_query=kql_query,
    server_query_type="KQL",
    scope_conditions={"Moniker": moniker},
)
```

Note: DGrep MCP tool returned permission errors for `Xstore`/`NativeFePerfMetric` events during validation (2026-03-05). This is expected — DGrep requires per-namespace permission grants for the calling identity. The query patterns above are verified against `jupyter-templates/` usage.

However, the DGrep tool **did successfully resolve account → tenant → moniker mappings**:

| Account | Storage Tenant | DGrep Moniker |
|---|---|---|
| xaiopsml | MS-SJC22PrdStr05C | MdsXstoreSJC2205C |
| xportals | MS-SJC23PrdStr01C | MdsXstoreSJC2301C |

Corresponding XArgus latency data (validated via Kusto, 2026-03-05 00:00–00:05 UTC):

**xaiopsml** (Tenant: MS-SJC22PrdStr05C):

| TimeWindow | Operation | EntityType | RequestCount | ServerTimeMs_Avg | ServerTimeMs_P99_0 | TsTimeMs_P99_0 | LastTS |
|---|---|---|---|---|---|---|---|
| 00:05 | GetBlobProperties | BlockBlob | 40 | 25.58 | 93.06 | 4.54 | ms-sjc22prdstr05d$xtableserver_in_7 |
| 00:05 | ListBlobs | Container | 1 | 1529.19 | 1529.19 | 1465.34 | ms-sjc22prdstr05d$xtableserver_in_7 |
| 00:00 | PutBlob | BlockBlob | 14 | 33.94 | 110.55 | 18.48 | ms-sjc22prdstr05d$xtableserver_in_7 |

**xportals** (Tenant: MS-SJC23PrdStr01C):

| TimeWindow | Operation | EntityType | RequestCount | ServerTimeMs_Avg | ServerTimeMs_P99_0 | TsTimeMs_P99_0 | LastTS |
|---|---|---|---|---|---|---|---|
| 00:05 | EntityGroupTransaction | Table | 24033 | 6.95 | 27.69 | 24.64 | ms-sjc23prdstr01c$xtableserver_in_143 |
| 00:05 | QueryEntity | Table | 2072 | 5.39 | 22.68 | 9.15 | ms-sjc23prdstr01c$xtableserver_in_143 |
| 00:05 | GetBlob | BlockBlob | 10 | 5.18 | 8.61 | 1.3 | ms-sjc23prdstr01c$xtableserver_in_217 |
