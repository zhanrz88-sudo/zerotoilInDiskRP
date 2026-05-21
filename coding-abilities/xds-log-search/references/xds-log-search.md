# XDS Log Search — Reference Examples

Usage patterns for `xstore.xds.search_log()`, `search_by_activity_id()`, and `generate_log_search_link()`.

> **CRITICAL — Log Volume & Retention Constraints (must follow)**
>
> | Log type | Max time window | Retention |
> |---|---|---|
> | **Verbose** | ≤ 5 minutes | ~2 days |
> | **Perf** | ≤ 5 minutes | ~2 days |
> | **Error** | ≤ 30 minutes | ~1 week |
> | **Status** | ≤ 30 minutes | ~1 week |
> | **All** | ≤ 2 minutes (use `top`) | varies by type |
>
> - Always set `top=N` when sampling or checking for pattern existence.
> - Prefer narrowing the time window using timestamps from other sources (DGrep, ICM, Kusto) before issuing an XDS log search.
> - If you need a longer range, split into multiple searches with smaller windows.
> - Always include `search_string` — never search without a filter.

## XACServer — verbose/error/status log search

### Search XACServer verbose for LLAM processing status

```python
from xstore import xds
from datetime import timedelta

# Verbose: keep window ≤5min, use a known timestamp
xac_result = await xds.search_log(
    "<tenant_name>",
    timestamp - timedelta(minutes=1),
    timestamp + timedelta(minutes=1),
    ['xacserver'],
    log_type='Status',
    search_string="[ACU][LLAM] Processing Limitless Account migration command for account:<account_name>",
    top=10,  # We only need to confirm the pattern exists
)
xac_df = xac_result.to_df()
# Get activity id for deeper trace
xac_activityid = xac_df.iloc[0].activityId
```

> **Source:** [jupyter-templates/Xstore/Limitless/Triage Stuck LLAM Migrations.ipynb](../../../jupyter-templates/Xstore/Limitless/Triage%20Stuck%20LLAM%20Migrations.ipynb)

### Follow XACServer activity id for all log levels

```python
# When searching by activity_id, the scope is narrow, so 'All' is safe here
xac_all_result = await xds.search_log(
    "<tenant_name>",
    timestamp - timedelta(minutes=1),
    timestamp + timedelta(minutes=1),
    ['xacserver'],
    log_type='All',
    activity_id=xac_activityid,
    top=200,  # Cap in case of unusually chatty request
)
xac_all_df = xac_all_result.to_df()
# Filter to errors
xac_errors = xac_all_df[xac_all_df['level'] == 'error']
```

> **Source:** [jupyter-templates/Xstore/Limitless/Triage Stuck LLAM Migrations.ipynb](../../../jupyter-templates/Xstore/Limitless/Triage%20Stuck%20LLAM%20Migrations.ipynb)

### Search XACServer error logs by account name

```python
result = await xds.search_log(
    "<tenant_name>",
    start_time,
    end_time,
    ['xacserver'],
    log_type='Error',
    search_string="<account_name>",
)
df = result.to_df()
error_message = df.iloc[0]['message']
component_name = df.iloc[0]['componentName']
```

> **Source:** [jupyter-templates/Xstore/Location Service/AnalyzeStuckLLAMMigrationOnStamp.ipynb](../../../jupyter-templates/Xstore/Location%20Service/AnalyzeStuckLLAMMigrationOnStamp.ipynb)

## XTableMaster — error log search

### Search TableMaster for common LLAM errors

Common error patterns to scan for in XACServer/TableMaster logs:

```python
common_errors = [
    "Remote BC NOT complete",
    "0x830a280e",
    "[LLAM][XAC] Geo replayer not caught up for",
    "is not eligable to be scheduled",
    "[LLAM] Cannot split",
    "[LLAM][XAC] Invalid transition from",
    "[ACU] Unknow table name",
    "[ACU] Job failed",
]

for error_pattern in common_errors:
    filtered = df[df['message'].str.contains(error_pattern, na=False)]
    if len(filtered) > 0:
        print(f"Found: {filtered.iloc[0]['message']}")
        break
```

> **Source:** [jupyter-templates/Xstore/Limitless/Triage Stuck LLAM Migrations.ipynb](../../../jupyter-templates/Xstore/Limitless/Triage%20Stuck%20LLAM%20Migrations.ipynb)

### Detect LLAM split block in TableMaster log

For the failover TSG, the key pattern in TableMaster error log:

```python
tm_result = await xds.search_log(
    "<tenant_name>",
    from_time,
    to_time,
    ['xtablemaster'],
    log_type='Error',
    search_string="<account_name>",
)
tm_df = tm_result.to_df()

# Check for LLAM split failure
llam_split = tm_df[tm_df['message'].str.contains('Cannot split partition', na=False)]
if not llam_split.empty:
    msg = llam_split.iloc[0]['message']
    if 'Incompatible LLAM Stage' in msg:
        print("LLAM split block — transfer to StorageCRM")
    else:
        print("Other split failure — transfer to TableMaster team")
```

> **Pattern based on TSG:** failover-pending-transaction-primary-stuck-prepare-failover Step 4

## Nephos.Account — perf log search

### Search Nephos.Account perf logs for LLAM migration

```python
# Perf: keep window ≤5min
result = await xds.search_log(
    "<tenant_name>",
    start_time,
    end_time,  # Ensure (end_time - start_time) ≤ 5 minutes
    ['nephos.account'],
    log_type='Perf',
    search_string='Account=<account_name> Operation=LimitLessMigrateAccount',
    top=20,  # Sample the first few perf entries
)
df = result.to_df()
activity_id = df.iloc[0]['activityId']
timestamp = df.iloc[0]['timestamp']
```

> **Source:** [jupyter-templates/Xstore/Location Service/AnalyzeStuckLLAMMigrationOnStamp.ipynb](../../../jupyter-templates/Xstore/Location%20Service/AnalyzeStuckLLAMMigrationOnStamp.ipynb)

### Search Nephos.Account for PollFailover and check GeoConfigOffCounter

```python
# Perf logs: keep window ≤5min
acct_result = await xds.search_log(
    "<tenant_name>",
    from_time,
    to_time,  # Ensure (to_time - from_time) ≤ 5 minutes
    ['nephos.account'],
    log_type='Perf',
    search_string="<account_name>",
    top=50,  # Sample enough to find a PollFailover call
)
acct_df = acct_result.to_df()

# Pick one PollFailover call and trace its activity id
poll_entries = acct_df[acct_df['message'].str.contains('PollFailover', na=False)]
if not poll_entries.empty:
    aid = poll_entries.iloc[0]['activityId']
    trace = await xds.search_by_activity_id(aid, entry_level_only=True)
    trace_df = trace.to_df()
    # Check for GeoConfigOffCounter > 0
    geo_off = trace_df[trace_df['message'].str.contains(r'GeoConfigOffCounter=\d+', na=False, regex=True)]
    if not geo_off.empty:
        print("GeoConfigOff detected — RA ximi@microsoft.com")
```

> **Pattern based on TSG:** failover-pending-transaction-primary-stuck-prepare-failover Step 4

## Nephos.Blob — verbose log search

### Search FE verbose logs for a specific request

```python
# Verbose: keep window ≤5min, use top for sampling
result = await xds.search_log(
    "<tenant_name>",
    start_time,
    end_time,  # Ensure (end_time - start_time) ≤ 5 minutes
    ['nephos.blob'],
    log_type='Verbose',
    search_string='[XIscsiTarget] SCSI: SCSI WRITE(10)',
    top=20,  # Sample — verbose logs are extremely high volume
)
result.show()
df = result.to_df()
```

> **Source:** [jupyter-templates/Xstore/Developer/amlankusum/LogSearchIscsi2.ipynb](../../../jupyter-templates/Xstore/Developer/amlankusum/LogSearchIscsi2.ipynb)

## Activity ID tracing

### Search by activity id (entry-level only)

```python
result = await xds.search_by_activity_id(
    '<activity_id>',
    entry_level_only=True,
)
result.show()
df = result.to_df()
```

> **Source:** [jupyter-snippets/public.json](../../../jupyter-snippets/public.json) — snippet "Search xds log by activity id"

### End-to-end tracing across layers

```python
result = await xds.search_by_activity_id(
    '<activity_id>',
    entry_level_only=False,  # traces across FE → TS → EnPn → CSM
)
df = result.to_df()
```

> **Source:** [jupyter-templates/Xstore/Health/MBTServerLogFetcher.ipynb](../../../jupyter-templates/Xstore/Health/MBTServerLogFetcher.ipynb)

## Generate shareable log search links

### Generate a link for XTableMaster status logs

```python
link = await xds.generate_log_search_link(
    "<tenant_name>",
    start_time,
    end_time,
    'xtablemaster',
    "<tenant_name>",
    log_type='Status',
    search_string="<partition_name>",
)
print(link)
```

> **Source:** [jupyter-templates/Xstore/XDiskAvailability/rmainiBackup/Red Report Backup 01222026.ipynb](../../../jupyter-templates/Xstore/XDiskAvailability/rmainiBackup/Red%20Report%20Backup%2001222026.ipynb)

### Generate a link with regex search

```python
link = await xds.generate_log_search_link(
    "<tenant_name>",
    start_time,
    end_time,
    "<ts_instance_name>",
    "<tenant_name>",
    log_type='Status',
    search_string_type='Regex',
    search_string='loadStart.*<partition_name>',
)
print(link)
```

> **Source:** [jupyter-templates/Xstore/XDiskAvailability/rmainiBackup/Red Report Backup 01222026.ipynb](../../../jupyter-templates/Xstore/XDiskAvailability/rmainiBackup/Red%20Report%20Backup%2001222026.ipynb)
