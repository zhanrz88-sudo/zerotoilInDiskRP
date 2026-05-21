---
name: MDM - Query metrics
description: Query MDM metric time series (KQL-m) and convert results to a DataFrame.
---

# Coding Ability: mdm-query

## Description
Queries MDM metric time series data using the `xportal.mdm` client (KQL-m) and converts the result to a Pandas DataFrame.

- Intended for code generation building blocks.
- Read-only by default.

Prereqs

- Run inside an environment where `xportal` is available.
- You must know the `mdm_account` to query.

## Remarks

Interfaces (from `zero-toil/.venv/Lib/site-packages/xportal/mdm.py`)

- `await mdm.query(metric_account: str, start_time: datetime, end_time: datetime, kql_query: str) -> MetricQueryResult`
  - `start_time` / `end_time` are `datetime` objects (UTC timezone-aware is recommended).
  - `kql_query` is a KQL-m query string.

- Return type: `MetricQueryResult`
  - Data members:
    - `Timestamp: List[datetime]`
    - `Fields: List[object]` (each entry includes dimension metadata and sampling type)
    - `Values: List[List[float]]`
  - Helpers:
    - `to_df() -> pandas.DataFrame` (columns are derived from the dimension values)
    - `show(columns: Optional[List[str]] = None) -> None` (matplotlib line chart)

## Sample Python code

```python
import datetime

from xportal import mdm


mdm_account = "<mdm_account>"
kqlm_query = """
metricNamespace(\"<NAMESPACE>\")
  .metric(\"<METRIC>\")
  .dimensions(\"<DIMENSION>\")
  .samplingTypes(\"<SAMPLING_TYPE>\")
| take 10
""".strip()

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(hours=1)

result = await mdm.query(mdm_account, start_time, end_time, kqlm_query)
df = result.to_df()

df.head(50)
```
