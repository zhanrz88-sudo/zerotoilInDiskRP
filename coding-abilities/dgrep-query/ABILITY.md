---
name: dgrep-query
description: Query DGrep logs and convert results to a DataFrame.
---

# Coding Ability: dgrep-query

## Description
Queries DGrep (distributed grep) logs using the `xportal.dgrep` client.

DGrep is a distributed log search system that scans logs stored across many storage accounts (called **monikers**). It is fundamentally different from Kusto: DGrep does not have indexed tables — it scans raw log files in storage, so queries are **I/O-intensive** and **load-sensitive**.

- Intended for code generation building blocks.
- Read-only by default.
- **Always use `scope_conditions`** (especially `Moniker`) to limit the storage accounts scanned. Without scope conditions, a DGrep query can be extremely slow or time out.
- **Keep time windows small** (5–10 minutes is ideal). Large windows cause excessive load.
- **Use `dgrep_query_with_retry()` from `zerotoil.core.framework` in generated TSG code** so DGrep throttling (HTTP 503/429 or outstanding-query quota) backs off instead of failing the run immediately.
- For curated sample query patterns, see `references/` under this coding ability folder.

Key concepts

- **Namespace**: The log source category (e.g., `Xstore`, `XHealth`, `DataBoxCopyRole`).
- **Event name**: The specific log event table (e.g., `NativeFePerfMetric`, `PartitionStats`, `PartitionDowntimeEvent`).
- **Moniker**: The DGrep storage account moniker that logs are written to. Each XStore tenant has a specific moniker. Use `get_moniker_by_xstore_tenant()` to resolve it.
- **Scope conditions**: A dict that narrows which storage accounts + roles to scan. Common keys: `Moniker`, `Role`, `Tenant`, `TagStorageStamp`.

Query languages

- **MQL** (default): DGrep's native query language. Uses `.Contains()`, `.StartsWith()`, `select`, `where` syntax.
  - Example: `where Partition.Contains("<partition>") select Host, Partition, PreciseTimeStamp`
- **KQL**: Standard Kusto Query Language, supported via `server_query_type='KQL'`.
  - Example: `source | where Status != "Success" | project Status, HttpStatusCode | take 10`
- Both can be used for `server_query` and `client_query` independently.

Server query vs client query

- DGrep scans data stored across many storage blobs. The **server query** runs independently on each blob (not aggregated across blobs). The **client query** runs on the combined results from all blobs.
- **Filtering / projection only** (where, select/project): put everything in `server_query`. This reduces network transfer and uses remote compute.
- **Aggregation** (summarize, count, top, orderby): you need **both**:
  - `server_query`: filter + project to reduce data transferred over the network.
  - `client_query`: aggregate / sort / take on the combined results from all blobs.
- Example pattern for aggregation:
  ```python
  # Server: filter + reduce columns (runs per blob)
  server_query = 'where Status != "Success" select Account, Status, PreciseTimeStamp'
  # Client: aggregate across all blobs
  client_query = 'orderby PreciseTimeStamp asc'
  
  result = await dgrep.query(
      namespace, event_name, start_time, end_time,
      server_query=server_query,
      client_query=client_query,
      scope_conditions=scope_conditions,
  )
  ```

Prereqs

- Run inside an environment where `xportal` is available.
- The managed service identity must have DGrep read permission for the target namespace/events.

## Remarks

Interfaces (from `zero-toil/.venv/Lib/site-packages/xportal/dgrep.py`)

- `await dgrep.query(
        namespaces: Union[str, List[str]],
        event_names: Union[str, List[str]],
        from_time: datetime.datetime,
        to_time: datetime.datetime,
        server_query: Optional[str] = None,
        server_query_type: str = "MQL",
        scope_conditions: Optional[dict] = None,
        client_query: Optional[str] = None,
        client_query_type: str = "MQL",
        environment: Optional[str] = None,
    ) -> DGrepQueryResult`

  - `namespaces` can be a single string or a list (e.g., `['DataBoxCopyRole', 'DataBoxDiag']`).
  - `event_names` can be a single string or a list.
  - `server_query_type` / `client_query_type`: `"MQL"` (default) or `"KQL"`.
  - `scope_conditions`: dict where values can be strings or lists of strings.
    - Internally, `Moniker` → `MonikerRegex`, `Region` → `LocationRegex`.
    - For Xstore namespace, `TagStorageStamp` is also treated as a moniker.
  - `environment` (optional): `"Production"`, `"Mooncake"`, `"Fairfax"`, `"USNat"`, `"USSec"`.

- Return type: `DGrepQueryResult`
    - Data members: `Fields: List[str]`, `Data: List[List[Any]]`
    - Helpers: `to_df() -> pandas.DataFrame`, `to_dict() -> dict`, `show(columns: Optional[List[str]] = None) -> None`
    - Share link: `get_dgrep_link() -> str`

Static link helper (no query execution)

- `dgrep.get_dgrep_link(namespaces, event_names, from_time, to_time, server_query=None, server_query_type='MQL', scope_conditions=None, ...) -> str`

Moniker resolution helper (from `xstore.common.dgrep`)

- `await get_moniker_by_xstore_tenant(tenant_name: str) -> str`
  - Usage: `from xstore.common.dgrep import get_moniker_by_xstore_tenant`

Alternative moniker via tenant entity

- `f'MdsXstore{tenant_entity.Moniker}'` where `tenant_entity = await get_tenant(tenant_name)`

Common scope condition patterns (from templates)

- Xstore FE perf: `{'Moniker': await get_moniker_by_xstore_tenant(tenant_name)}`
- Xstore event grid: `{'Moniker': f'MdsXstore{tenant_entity.Moniker}'}`
- Cosmos Store Gen2: `{'TagStorageStamp': moniker, 'Tenant': tenant_name}`
- DataBox: `{'Tenant': [tenant], 'Role': ['CopyRole']}`
- Limitless XAC: `{'Tenant': 'rsrp' + account_entity.ArmRegionName}`

Generated ZeroToil retry helper

- `await dgrep_query_with_retry(dgrep, **query_kwargs)` from `zerotoil.core.framework`
  - Wraps `dgrep.query()` with exponential backoff.
  - Retries known throttle/transient errors: HTTP 503, HTTP 429, `ServiceUnavailable`, `throttl`, and `Reached maximum number of outstanding queries from this client`.
  - Raises non-throttle errors immediately.
  - Use this helper for all DGrep calls generated inside TSG Python modules.

Common namespace + event combinations (from templates)

| Namespace | Event(s) | Purpose |
|---|---|---|
| `Xstore` | `NativeFePerfMetric`, `FrontEndSummaryPerfLogs` | FE request failure/latency analysis |
| `Xstore` | `PartitionStats`, `PartitionStatsEx1`, `PartitionStatsEx3` | Partition-level health stats |
| `Xstore` | `PartitionDowntimeEvent` | Partition downtime tracking |
| `XHealth` | `XLivesiteLog` | XStore livesite/health alerts |
| `DataBoxCopyRole`, `DataBoxDiag` | `DataEvent` | DataBox copy job logs |

Important: field availability per event

- **Not all events have the same fields.** For example, `PartitionStats` does NOT have a `Tenant` field. Filtering `where Tenant == "..."` will fail with a field-not-found error.
- When in doubt, rely on **scope conditions** (especially `Moniker`) to limit to the correct tenant's data instead of filtering by `Tenant` in the query itself.
- Use `select` (MQL) or `project` (KQL) to only request fields you know exist in the event.

## Sample Python code

```python
import datetime
from xportal import dgrep
from xstore.common.dgrep import get_moniker_by_xstore_tenant
from zerotoil.core.framework import dgrep_query_with_retry

tenant_name = "<tenant_name>"  # e.g. "MS-AM5PrdStr04A"

# Resolve DGrep moniker for the tenant
moniker = await get_moniker_by_xstore_tenant(tenant_name)

namespace = "Xstore"
event_name = "NativeFePerfMetric"

# MQL query (default) — use .Contains(), select syntax
server_query = 'where Status != "Success" select Account, Status, HttpStatusCode, InternalStatus, PreciseTimeStamp'

# Scope conditions — CRITICAL for performance
scope_conditions = {"Moniker": moniker}
```

## Important: RSRP Tenant Scoping

For **RegionalSRP** namespace events (e.g., `ServiceBackgroundActivityEvent`, `AccountFailoverStatisticsEvent`), use the **RSRP tenant name** directly as a scope condition — do NOT try to resolve it via `get_moniker_by_xstore_tenant()` (it will fail with a regex pattern mismatch).

```python
# CORRECT — scope with Tenant for RegionalSRP namespace
result = await dgrep.query(
    namespaces="RegionalSRP",
    event_names="ServiceBackgroundActivityEvent",
    from_time=from_time,
    to_time=to_time,
    server_query='where it.any("LogPendingFailoverTransactionAlertEvent") select PreciseTimeStamp, Message, ActivityId',
    server_query_type="MQL",
    scope_conditions={"Tenant": "RSRPWestUS"},  # RSRP name, NOT storage tenant
    environment="Production",
)
```

**Gotcha:** Not all DGrep events exist for all tenant types. For RSRP tenants:
- ✅ `ServiceBackgroundActivityEvent` — alert/watchdog data
- ❌ `AccountFailoverStatisticsEvent` — NEVER exists (always 0 rows)
- ❌ `AccountFailoverEvent` — NEVER exists (always 0 rows)

Always implement fallback chains when using DGrep events that may not exist for certain tenant types.

# Keep time window small (5–10 minutes)
end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=5)

result = await dgrep_query_with_retry(
    dgrep,
    namespaces=namespace,
    event_names=event_name,
    from_time=start_time,
    to_time=end_time,
    server_query=server_query,
    scope_conditions=scope_conditions,
)

df = result.to_df()
df.head(20)

# Sharable link
dgrep_link = result.get_dgrep_link()
dgrep_link
```

### Alternative: KQL server query

```python
# KQL mode — use standard Kusto syntax
kql_query = """
source
| where Status != "Success"
| project Account, Status, HttpStatusCode, InternalStatus, PreciseTimeStamp
| take 20
""".strip()

result = await dgrep.query(
    namespace,
    event_name,
    start_time,
    end_time,
    server_query=kql_query,
    server_query_type="KQL",
    scope_conditions=scope_conditions,
)
```
