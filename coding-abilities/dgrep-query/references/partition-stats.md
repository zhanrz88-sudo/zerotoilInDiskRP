# Partition stats / downtime DGrep patterns

These examples query partition-level health stats and downtime events for XStore tenants.

Namespace: `Xstore`
Events: `PartitionStats`, `PartitionStatsEx1`, `PartitionStatsEx3`, `PartitionDowntimeEvent`

## Moniker resolution (required)

```python
from xstore.common.dgrep import get_moniker_by_xstore_tenant

tenant_name = "<tenant_name>"  # e.g. "MS-AM5PrdStr04A"
moniker = await get_moniker_by_xstore_tenant(tenant_name)
scope_conditions = {"Moniker": moniker}
```

## Example: Partition stats (MQL)

```python
import datetime
from xportal import dgrep

partition = "<partition_name>"  # e.g. the partition key from an alert

# MQL — .Contains() + select
query = f'where Partition.Contains("{partition}") select Host, MaxStmTtlExtCntSt, MaxStmTtlExtCnt, Partition, PreciseTimeStamp, GeoBytesSentSec, NewGeoMsgCnt, NewGeoMsgPndCnt, RetryGeoMsgPndCnt, SenderLagSeconds'

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=10)

result = await dgrep.query(
    "Xstore", "PartitionStats", start_time, end_time,
    server_query=query,
    scope_conditions=scope_conditions,
)

df = result.to_df()
```

## Example: Partition stats extended (PartitionStatsEx3)

```python
query = f'where Partition.Contains("{partition}") select LogStmTtlExtCnt, Partition, PreciseTimeStamp'

result = await dgrep.query(
    "Xstore", "PartitionStatsEx3", start_time, end_time,
    server_query=query,
    scope_conditions=scope_conditions,
)
```

## Example: Partition downtime events

```python
from xstore import get_tenant

tenant_entity = await get_tenant(tenant_name)
scope_conditions = {"Moniker": f"MdsXstore{tenant_entity.Moniker}"}

query = f'where It.Any("{partition}")'

result = await dgrep.query(
    "Xstore", "PartitionDowntimeEvent", start_time, end_time,
    server_query=query,
    scope_conditions=scope_conditions,
)

result.show()
df = result.to_df()
```

Inspired by:
- jupyter-templates/Xstore/XInvestigator/CollectPartitionInfoAndCheckRepeatedOffender.ipynb
- jupyter-templates/Xstore/XTable/DataCorruptionFENodeAnalysis.ipynb
- jupyter-templates/Xstore/XTable/TSHighLatencyAnalysis.ipynb

## Notes on MQL query syntax

Common MQL patterns used in partition queries:

| Pattern | Meaning |
|---|---|
| `where Field.Contains("value")` | Field contains substring |
| `where Field.StartsWith("value")` | Field starts with |
| `where Field == "value"` | Exact match |
| `where Field ~= "regex"` | Regex match |
| `where It.Any("value")` | Any field contains value |
| `select Field1, Field2` | Project specific fields |
| `orderby PreciseTimeStamp asc` | Client-side ordering |

## Important: PartitionStats does NOT have a `Tenant` field

Querying `where Tenant == "..."` on PartitionStats will fail with:
> `No property or field 'Tenant' exists in type 'DynamicClass_437'`

Instead, rely on **scope conditions with Moniker** to limit to the correct tenant's storage. The moniker already scopes to the correct tenant's data.

## Verified sample result (queried 2026-03-05, tenant MS-SJC22PrdStr05C, moniker MdsXstoreSJC2205C)

Query: `select Host, Partition, MaxStmTtlExtCnt, MaxStmTtlExtCntSt, GeoBytesSentSec, NewGeoMsgCnt, NewGeoMsgPndCnt, SenderLagSeconds, PreciseTimeStamp`
Event: `PartitionStats`, Time window: 00:00–00:05 UTC

| MaxStmTtlExtCntSt | MaxStmTtlExtCnt | NewGeoMsgPndCnt | SenderLagSeconds | PreciseTimeStamp |
|---|---|---|---|---|
| PageData | 41 | 0 | 0 | 2026-03-05T00:04:33.682Z |
| PageData | 41 | 0 | 0 | 2026-03-05T00:04:33.682Z |
| PageData | 37 | 0 | 0 | 2026-03-05T00:04:33.682Z |

(160 rows total returned in 5-minute window — confirms the query pattern works)

## Account → Tenant → Moniker mapping reference

| Account | Storage Tenant | DGrep Moniker |
|---|---|---|
| xaiopsml | MS-SJC22PrdStr05C | MdsXstoreSJC2205C |
| xportals | MS-SJC23PrdStr01C | MdsXstoreSJC2301C |
