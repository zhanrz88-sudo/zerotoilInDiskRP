# XTable / XStream / XCompute API patterns

These examples show how to use the data-plane XDS APIs for reading table data, stream info, and XCompute jobs.

## Example: Read an XTable (using xds_client directly)

```python
from xds_client import XTableApi, ReadTableArgs, RowKeyArgs, ApiClient

tenant_name = "<tenant_name>"

client = ApiClient()
await client.connect_tenant(tenant_name)
xtable = XTableApi(client)

args = ReadTableArgs(
    table_name="<table_name>",  # e.g. "XStoreAccounts"
    row_key_low=RowKeyArgs(components=["<low_key>"]),
    row_key_high=RowKeyArgs(components=["<high_key>"]),
    max_rows_to_return=10,
)
result = await xtable.x_table_read_table(args)
print(result)
```

Inspired by:
- jupyter-templates/Xstore/XInvestigator/SmokeTest.ipynb
- jupyter-templates/Xstore/XTable/AccountsServedByPartition.ipynb
- jupyter-templates/Xstore/XTable/CopyBlobEngine/AsyncCopy404.ipynb

## Example: Read an XTable (using the XdsApiClient wrapper)

```python
from xstore.common.xds import XdsApiClient

client = XdsApiClient(tenant="<tenant_name>", environment="Production")
await client.connect()

result = await client.read_table(
    "<table_name>",
    key_low=["<low_key>"],
    key_high=["<high_key>"],
    max_rows_to_return=10,
)
if result and result.rows:
    for row in result.rows[:5]:
        print(row)
```

Inspired by:
- jupyter-templates/Xstore/XTable/GC/AutoTSG/EncryptionFailureDiagnostic.ipynb
- jupyter-templates/Xstore/XTable/XBlob/Experiments/BatchOD.ipynb

## Example: XStream API access

```python
from xds_client import XStreamApi, ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
xstream = XStreamApi(client)

# Example: get stream info (method depends on specific need)
# result = await xstream.x_stream_<method_name>(...)
```

Inspired by:
- jupyter-templates/Xstore/Stream/ZRS/ZRSReportTmp2.ipynb
- jupyter-templates/Xstore/XInvestigator/mooncakeTest.ipynb

## Example: XCompute job query

```python
from xds_client.api.x_compute_api import XComputeApi
from xds_client import ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
xcompute = XComputeApi(client)

# Query XCompute jobs for the tenant
# result = await xcompute.x_compute_<method_name>(...)
```

Inspired by:
- jupyter-templates/Xstore/XTable/GC/AutoTSG/LongTimeNoRunXComputeJobs.ipynb
- jupyter-templates/Xstore/XTable/GC/AutoTSG/XComputeJobFailureIcmTrace.ipynb

## Example: Config rollout query

```python
from xds_client import ConfigRolloutApi, ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
config_api = ConfigRolloutApi(client)

# Query config rollout info
# result = await config_api.config_rollout_<method_name>(...)
```

Inspired by:
- jupyter-templates/Xstore/XTable/XBlob/AutomaticXBBCapacityManagement/CloseICMForAutoRevert.ipynb

## Example: Get partition stats for a specific table (equivalent to Get-XdsPartition)

The PowerShell `Get-XdsPartition -Tenant <tenant> -Table <table> -Account <account>` cmdlet
maps to `XTableApi.x_table_get_partitions_stats()` with client-side account filtering.

The cmdlet (defined in `src/XTable/Tools/XDiagCmdLet/XdsXtable.cs`) calls
`xdsClient.GetTablePartitions(tableName)` which hits the REST endpoint
`GET /api/partitionsStats?pageNumber=N&ifModifiedSince=...`. It then locally
filters rows by account key range using `Helpers.FilterRowByAccount()`.

The Python equivalent is implemented in `jupyter-templates/Xstore/XDiagCmdLet.ipynb`
as `GetXdsPartitionStat()`.

### Minimal call — get all partitions for a table

```python
import datetime
from xds_client import XTableApi, ApiClient

tenant = "<tenant_name>"  # e.g. "MS-SYD24PrdStr02A"

client = ApiClient()
await client.connect_tenant(tenant)
xtable = XTableApi(client)

# Paginate through all partitions
page_number = 0
all_partitions = []
while True:
    result = await xtable.x_table_get_partitions_stats(
        page_number=page_number,
        if_modified_since=datetime.datetime.min,
        add_table_info=True,
    )
    if result and result.rows:
        all_partitions.extend(result.rows)
    page_number += 1
    if not result or not result.continuation_key:
        break

# result.schema.columns contains column definitions
# result.rows is list[list[str]] — each row is a list of column values
print(f"Total partitions: {len(all_partitions)}")
```

Source: xds_client.api.x_table_api.XTableApi.x_table_get_partitions_stats (Swagger-generated)
Inspired by: jupyter-templates/Xstore/XDiagCmdLet.ipynb (GetXdsPartitionStat function, line 240)

### With account filtering (equivalent to `-Account` parameter)

The account filter works by constructing row key ranges from the account name
and filtering client-side, exactly as the C# cmdlet does. The `XDiagCmdLet.ipynb`
helper `GetXdsPartitionStat` implements this in Python using `ParseStringIntoKey`
and `XdsXtable.FilterRowByAccount`.

```python
import datetime
from xds_client import XTableApi, ApiClient

tenant = "<tenant_name>"
account = "<account_name>"  # e.g. "ppthdprod"

client = ApiClient()
await client.connect_tenant(tenant)
xtable = XTableApi(client)

# For account filtering, the notebook helper constructs RowKey bounds
# and filters client-side after each page. Simplified example:
page_number = 0
matched = []
while True:
    result = await xtable.x_table_get_partitions_stats(
        page_number=page_number,
        if_modified_since=datetime.datetime.min,
    )
    if result and result.rows and result.schema:
        # Find column index for account-related fields
        col_names = [c.name for c in result.schema.columns] if result.schema.columns else []
        # Filter rows containing the account name
        for row in result.rows:
            row_str = str(row)
            if account.lower() in row_str.lower():
                matched.append(dict(zip(col_names, row)))
    page_number += 1
    if not result or not result.continuation_key:
        break

print(f"Partitions for {account}: {len(matched)}")
for p in matched[:5]:
    print(p)
```

Source: xds_client.api.x_table_api.XTableApi.x_table_get_partitions_stats
Inspired by: jupyter-templates/Xstore/XDiagCmdLet.ipynb (GetXdsPartitionStat with account param)

### Get a single partition by name

```python
import datetime
from xds_client import XTableApi, ApiClient

tenant = "<tenant_name>"
partition_name = "xfiles!20250429062128_44d1b2df.meta"

client = ApiClient()
await client.connect_tenant(tenant)
xtable = XTableApi(client)

result = await xtable.x_table_get_partition_stats(
    partition_name=partition_name,
    if_modified_since=datetime.datetime.min,
)
# Returns a TableDataSet with schema, rows, metadata
if result and result.rows:
    col_names = [c.name for c in result.schema.columns] if result.schema.columns else []
    for row in result.rows:
        print(dict(zip(col_names, row)))
```

Source: xds_client.api.x_table_api.XTableApi.x_table_get_partition_stats

---

## Critical: RSRP Tenants vs Storage Tenants

RSRP (Regional SRP) tenant names (e.g., `RSRPWestUS`, `RSRPPublicPreprodEastUS2`) are **NOT** XDS storage tenants. They are SRP monitoring layer names used in DGrep `scope_conditions`.

**DGrep queries** use RSRP tenant names:
```python
await dgrep.query(
    scope_conditions={"Tenant": "RSRPPublicPreprodEastUS2"},
    namespaces="RegionalSRP",
    ...
)
```

**XDS API / log search** needs the **resolved storage tenant**:
```python
from xstore import get_account

# Resolve account → storage tenant
acct = await get_account("myaccount", environment="Production")
storage_tenant = acct.TenantName   # e.g., "MS-BY3PrdStev52A"
geo_pair = acct.GeoPairName        # e.g., "MS-MEL23PrdStr11D" or None

# Then use storage_tenant for XDS
await xds.search_log(storage_tenant, from_time, to_time, ...)
```

**Verified real mappings (2026-04-28):**

| Account | Storage Tenant | Geo-Pair | Account Type |
|---------|---------------|----------|-------------|
| dunghnsfailoversrc1 | MS-BY3PrdStev52A | None | None |
| bqhxscndsm10pe11cx | MS-DSM10PrdSte11D | None | None |
| apexhelpqueue | MS-SJC21PrdStr08A | None | StandardRAGRS |

**Note:** PUBLICPREPROD accounts may return `GeoPairName=None` and `AccountType=None`.

## DGrep Events Availability by Tenant Type

| DGrep Event | RSRP Tenants | Storage Tenants |
|-------------|-------------|-----------------|
| ServiceBackgroundActivityEvent (RegionalSRP) | ✅ Available | N/A |
| AccountFailoverStatisticsEvent (RegionalSRP) | ❌ **Never** | N/A |
| AccountFailoverEvent (RegionalSRP) | ❌ **Never** | N/A |
| XDS log search (search_log) | ❌ Not applicable | ✅ Available |

This means for FailoverPendingTransaction TSGs, you **must** implement fallbacks for Steps 2 and 3 since their primary DGrep data sources never exist for the tenant types that generate these incidents.

Inspired by: jupyter-templates/Xstore/XDiagCmdLet.ipynb (single partition branch, line 251)

### TableDataSet response structure

The `TableDataSet` model (from `xds_client.models.table_data_set`) has:

| Field | Type | Description |
|---|---|---|
| `schema` | `TableSchema` | Column definitions (`.name`, `.columns` list) |
| `metadata` | `dict[str, str]` | Key-value metadata |
| `rows` | `list[list[str]]` | Data rows — each row is a list of column values |
| `continuation_key` | `RowKey` | Pagination token — `None` when no more pages |

Source: xds_client/models/table_data_set.py (swagger_types at line 35)

## Example: Kusto alternative for XFiles GeoReplay partition check

When XDS API is not available or as a complementary data source, use the
`GeoReplayerBlockedPartitions2` Kusto table to check for XFiles partitions
in GeoReplay states (including LiveReplay).

```python
from xportal import kusto

tenant = "<tenant_name>"  # e.g. "MS-SYD24PrdStr02A"
account = "<account_name>"  # optional: filter by account in KeyLow

cluster = "xstore.kusto.windows.net"
database = "xstore"
query = f'''
    GeoReplayerBlockedPartitions2
    | where TimeStamp > ago(36h)
        and Tenant =~ "{tenant}"
        and Partition contains "xfiles!"
    | order by TimeStamp desc
    | take 1000
    | summarize by Partition, KeyLow, IsPausing, BootstrapGeoReplay
'''
result = await kusto.query(cluster, database, query)
df = result.to_df()
print(f"XFiles GeoReplay partitions: {len(df)}")
result.show()
```

GeoReplay state codes (from `jupyter-templates/Xstore/XSMB/GeoReplicationAutoAnalysis/Helper.ipynb`):

| Code | State |
|---|---|
| 101 | StopReplay |
| 102 | LiveReplay |
| 103 | LiveReplayPause |
| 104 | FlushReplay |
| 105 | FlushReplayDone |
| 106 | MigrationReplayDone |

Source: jupyter-templates/Xstore/XSMB/XFilesGeoReplayAccountFailoverCheck.ipynb (Kusto query, line 100)
Source: jupyter-templates/Xstore/XSMB/GeoReplicationAutoAnalysis/Helper.ipynb (state enum, line 206)

## Notes

- The `XdsApiClient` wrapper from `xstore.common.xds` is a convenience layer that auto-manages connection and provides `read_table()` for XTable access.
- For direct `xds_client` usage, instantiate an `ApiClient`, connect to a tenant, then pass the client to any API class constructor.
- Common XTable names used in templates: `XStoreAccounts`, partition tables, geo replication tables.
- `ReadTableArgs` requires `table_name`, `row_key_low`, `row_key_high`; optionally `max_rows_to_return`, `columns_to_return`.
- **PowerShell ↔ Python mapping**: `Get-XdsPartition -Tenant T -Table X -Account A` → `XTableApi.x_table_get_partitions_stats()` + client-side account filter (see XDiagCmdLet.ipynb).
- **Escalation ladder for partition checks**: 1) XDS API `x_table_get_partitions_stats()`; 2) Geneva Action `Invoke-XdsPartition`; 3) Kusto `GeoReplayerBlockedPartitions2`; 4) Manual fallback with full command for DRI.
