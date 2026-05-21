---
name: XDS Log Search
description: Search XDS role-level logs (verbose, error, status, perf) via xstore.xds — search_log, search_by_activity_id, generate_log_search_link.
---

# Coding Ability: xds-log-search

## Description

Searches XDS (XStore Deployment Service) role-level logs using the `xstore.xds` helper module. XDS logs capture verbose, error, status, and perf entries emitted by role instances (FE, TableServer, EnPn, CSM, XACServer, etc.) on storage tenants.

- **Read-only.** All search functions are non-mutating.
- Searches are **tenant-scoped** and require a **storage tenant** name (not an SRP tenant). See the `storage-account-tenant-metadata` coding ability to resolve the tenant from an account name.
- For XDS REST API calls (role instances, upgrade state, ping, XTable reads, etc.), see the `xds-api-call` coding ability.

**CRITICAL: SRP tenant vs storage tenant**

- **SRP tenants** (e.g., `RSRPAustraliaEast`) are Regional Storage Resource Provider control-plane tenants. XDS logs do **not** live on SRP tenants.
- **Storage tenants** (a.k.a. stamps, e.g., `MS-MEL23PrdStr11D`) are the physical clusters that host customer data and run XDS role instances. **`xds.search_log()` always requires a storage tenant.**
- To resolve the storage tenant from an account name, use `await get_account(account_name)` → `TenantName` field. For GRS accounts, the geo-pair tenant is in `GeoPairName`.

Prereqs

- Run inside an environment where `xstore` is available (XPortal Jupyter / XScript runtime).
- The managed service identity must have XDS access for the target tenant.

## Remarks

> **CRITICAL — Log Volume & Time Window Constraints**
>
> XDS logs are extremely high volume. Every user request generates many verbose entries and perf entries across FE/Table/Stream layers. A single tenant can handle tens of thousands of requests per second (default per-account RPS limit is 20,000, and a tenant can host thousands of accounts).
>
> **Maximum recommended time windows:**
> - **Verbose / Perf:** ≤ **5 minutes**. These logs are generated per-request per-layer and are by far the largest. Searching longer windows will hang or time out.
> - **Error / Status / other types:** ≤ **30 minutes**. Still high volume, but manageable in shorter windows.
> - **All:** Avoid `log_type='All'` unless the time window is very small (≤ 2 minutes) and you use `top` to cap results.
>
> **Log retention:**
> - Verbose and Perf logs are retained for **~2 days** only.
> - Error, Status, and other log types are retained for **~1 week** before garbage collection.
> - Do not search for logs older than these retention windows — they will not exist.
>
> **Use `top` for sampling / early exit:**
> - When you only need to confirm a pattern exists, or want a sample, always set `top=N` (e.g., `top=10`). The searcher will stop streaming as soon as `N` entries are collected, avoiding downloading the full result set.
> - Internally, `top` sets `RequiredNumberOfLogs` in the XDS request and triggers `_should_stop_search()` to abort the streaming loop early.
>
> **Strategies to avoid hanging searches:**
> 1. Narrow the time window using other data sources first (e.g., DGrep event timestamps, ICM incident create time, Kusto query results).
> 2. Use `search_string` to filter server-side — never search all logs without a filter.
> 3. Set `top=N` when sampling.
> 4. If you need to cover a longer time range, split into multiple sequential searches with smaller windows.
> 5. Use `activity_id` when available — it scopes the search to a single request trace.

### `search_log()` (from `xstore.common.xds`)

```python
from xstore import xds

result = await xds.search_log(
    tenant_name: str,
    from_time: datetime,
    to_time: datetime,
    role_instances: Union[str, List[str]],
    search_scope: str = None,
    log_type: str = 'All',             # 'All', 'Verbose', 'Error', 'Status', 'Perf', 'Custom'
    search_string: Union[str, List[str]] = None,
    search_string_type: str = 'PlainText',  # 'PlainText' or 'Regex'
    include_log_files: str = '',
    exclude_log_files: str = '*storagelogagent*',
    activity_id: str = None,
    top: int = None,
    retry_count: int = 0,
    debug: bool = False,
    return_partial_result: bool = True,
) -> XdsLogSearchEncapsulatedResult
```

- `tenant_name`: Full storage tenant name (e.g., `"MS-SN4PrdSte12C"`). Must be a storage tenant, never an SRP tenant.
- `role_instances`: Role name or instance name as string or list. Common role names: `'xacserver'`, `'xtablemaster'`, `'nephos.account'`, `'nephos.blob'`, `'xtableserver'`, `'enpn'`, `'csm'`, `'xnamespace'`. Role instance names are auto-normalized.
- `log_type`: Controls which log files are searched — `'Verbose'`, `'Error'`, `'Status'`, `'Perf'`, or `'All'`. Use `'Custom'` with `include_log_files` for specific file patterns.
- `search_string`: Filter log entries by text. Can be a single string or list of strings. Supports `'PlainText'` (default) or `'Regex'` via `search_string_type`.
- `top`: **Strongly recommended.** Limits the number of log entries returned. The searcher stops streaming as soon as `top` entries are collected. Use `top=10` for sampling, `top=100` for investigation. Omit only when you truly need all matching entries in a small time window.
- `search_scope`: Defaults to `tenant_name`. For limitless tenants, can be any tenant in the limitless group or `'All'`.
- `retry_count`: Retry logic for AKS cert-based auth environments where XDS allows only one search thread per service identity per tenant.
- `return_partial_result`: If `True` (default), returns partial results on timeout instead of raising.
- Returns `XdsLogSearchEncapsulatedResult`.

### `search_by_activity_id()`

```python
result = await xds.search_by_activity_id(
    activity_id: str,
    entry_level_only: bool = True,
    debug: bool = False,
    return_partial_result: bool = True,
    top: int = None,
) -> XdsLogSearchEncapsulatedResult
```

- Resolves tenant and role instance from the activity id automatically.
- `entry_level_only=True` (default): searches only the originating role instance.
- `entry_level_only=False`: enables end-to-end tracing across layers (FE → TS → EnPn → CSM). Slower but gives full request trace.

### `generate_log_search_link()`

Generates a shareable XDS log search URL without executing the search:

```python
link = await xds.generate_log_search_link(
    tenant_name: str,
    from_time: datetime,
    to_time: datetime,
    role_instances: Union[str, List[str]],
    search_scope: str = "",
    log_type: str = 'All',
    search_string: Optional[Union[str, List[str]]] = None,
    search_string_type: str = 'PlainText',
    include_log_files: str = '',
    exclude_log_files: str = '*storagelogagent*',
    activity_id: Optional[str] = None,
    output_format: str = 'Raw',  # 'Text', 'Formatted', 'Xml', 'Raw', 'Debug'
) -> str
```

### `XdsLogSearchEncapsulatedResult`

Return type for all search functions:

| Method/Field | Type | Description |
|---|---|---|
| `to_df()` | `pandas.DataFrame` | Convert to DataFrame. Columns: `componentName`, `level`, `timestamp`, `module`, `component`, `srcFile`, `srcFunc`, `srcLine`, `pid`, `tid`, `message`, `activityId`, `entryId`, `logFileName` |
| `show()` | display | Interactive HTML log viewer in Jupyter |
| `LogSearchUrl` | `str` | URL to the log search result |

### `ROLE_LOGFILE_MAPPINGS`

Built-in role to log file pattern map:

| Role Name | Log File Pattern |
|---|---|
| `XACServer` | `*_XACServer*` |
| `XTableMaster` | `*_XTableMaster*` |
| `XTableServer` / `XTableServer2` | `*_XTableServer*` |
| `CSM` | `*_csm*` |
| `EnPn` | `*_en*` |
| `XNamespace` | `*_XNamespace*` |
| `XLockServer` | `*_XLockServer*` |
| `XCacheMaster` | `_XCacheMaster*` |
| `XCacheNode` | `*_XCacheNode*` |
| `CosmosNameServer` | `*_CosmosNameServer*` |
| `StorageDiagnostics` | `*_StorageDiagnostics*` |

Note: `Nephos.Account`, `Nephos.Blob`, etc. are passed as role instance names directly (not in `ROLE_LOGFILE_MAPPINGS`).

## Sample Python code

```python
from xstore import xds
from datetime import datetime, timedelta

tenant_name = "<tenant_name>"  # e.g. "MS-SN4PrdSte12C"
account_name = "<account_name>"

# IMPORTANT: Use tight time windows to avoid hanging searches.
# For verbose/perf: max 5 minutes. For error/status: max 30 minutes.
# Prefer narrowing via a known timestamp (e.g., from DGrep, ICM, or Kusto).
event_time = datetime.utcnow()  # Replace with a known event timestamp when available

# --- Search XACServer verbose logs (≤5min window, with top) ---
xac_result = await xds.search_log(
    tenant_name,
    event_time - timedelta(minutes=2),
    event_time + timedelta(minutes=2),
    ['xacserver'],
    log_type='Verbose',
    search_string=account_name,
    top=50,  # Stop after 50 entries — remove only if you need ALL entries
)
xac_df = xac_result.to_df()
print(f"Found {len(xac_df)} XACServer log entries")

# --- Search TableMaster error logs (≤30min window) ---
tm_result = await xds.search_log(
    tenant_name,
    event_time - timedelta(minutes=15),
    event_time + timedelta(minutes=15),
    ['xtablemaster'],
    log_type='Error',
    search_string=account_name,
)
tm_df = tm_result.to_df()
llam_errors = tm_df[tm_df['message'].str.contains('Cannot split partition', na=False)]
print(f"Found {len(llam_errors)} split failure entries")

# --- Search Nephos.Account perf logs (≤5min window, with top) ---
acct_result = await xds.search_log(
    tenant_name,
    event_time - timedelta(minutes=2),
    event_time + timedelta(minutes=2),
    ['nephos.account'],
    log_type='Perf',
    search_string=account_name,
    top=20,  # Sample a few perf entries
)
acct_df = acct_result.to_df()

# --- Follow an activity id for full trace ---
if not acct_df.empty:
    activity_id = acct_df.iloc[0]['activityId']
    trace_result = await xds.search_by_activity_id(activity_id, entry_level_only=True)
    trace_df = trace_result.to_df()
    geo_off = trace_df[trace_df['message'].str.contains('GeoConfigOffCounter', na=False)]
    print(f"GeoConfigOff entries: {len(geo_off)}")

# --- Generate a shareable link (no time window limit — link is not executed here) ---
link = await xds.generate_log_search_link(
    tenant_name,
    event_time - timedelta(minutes=15),
    event_time + timedelta(minutes=15),
    ['xacserver'],
    log_type='Error',
    search_string=account_name,
)
print(f"Log search link: {link}")
```

## Known Log Message Formats

### Nephos.Account / Nephos.Blob Perf Logs

Perf log entries use a flat key-value format. Confirmed schema from real data:

```
Perf: PerfCounters: Account=<account> Operation=<op_name> on Container=<container> with Status=<status> RequestHeaderSize=<N> RequestSize=<N> ResponseHeaderSize=<N> ResponseSize=<N> ErrorResponseByte=<N> TimeInMs=<N> ProcessingTimeInMs=<N> ... HttpStatusCode=<N> ... InternalStatus=<internal_status> ... AuthenticationType='<auth>' ...
```

**Key fields for TSG pattern matching:**

| Key | Example Values | Use |
|---|---|---|
| `Operation` | `PostFailoverCleanup`, `PollFailover`, `GetBlobServiceProperties` | Identify the operation type |
| `Status` | `InternalError`, `Success`, `NetworkError` | Request outcome |
| `HttpStatusCode` | `500`, `200`, `503` | HTTP-level status |
| `InternalStatus` | `ServerOtherError`, `Success` | Internal classification |
| `Account` | `ppthdprod` | Target storage account |
| `TimeInMs` | `125.000000` | Total request latency |

**DataFrame columns** (from `to_df()`):

| Column | Example | Notes |
|---|---|---|
| `componentName` | `ms-syd24prdstr02a$nephos.account_in_5` | `<stamp>$<role>_in_<N>` |
| `level` | `perf` | Always `perf` for perf logs |
| `timestamp` | `2026-03-28 15:48:05.951280` | UTC timestamp |
| `module` | `CsClient` | Source module |
| `component` | `NephosAccount.exe` | Executable name |
| `srcFile` | `PerfCounterLogProcessor.cs` | Source file |
| `srcFunc` | `LogPerfCounter` | Source function |
| `message` | `Perf: PerfCounters: Account=...` | Full key-value message |
| `activityId` | `9AAF1420-0004-0005-71CA-BE042C000000` | Request activity id |
| `entryId` | `null` | Often null for perf entries |
| `logFileName` | `cosmosPerfLog_NephosAccount.exe_002451.bin` | Binary log file name |

**Filtering by operation:**
```python
# Find PollFailover entries
poll_entries = df[df['message'].str.contains('PollFailover', na=False)]

# Find PostFailoverCleanup errors
cleanup_errors = df[
    df['message'].str.contains('PostFailoverCleanup', na=False) &
    df['message'].str.contains('Status=InternalError', na=False)
]
```
