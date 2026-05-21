---
name: kusto-query
description: Run an ADX (Kusto) query and convert results to a DataFrame.
---

# Coding Ability: kusto-query

## Description
Runs a Kusto (ADX) query using the `xportal.kusto` client and converts the result to a Pandas DataFrame.

- Intended for code generation building blocks.
- Read-only by default.
- `cluster` + `database` are correctness-critical inputs: the tables/functions referenced by a KQL query only exist in specific clusters/databases.
- When generating sample KQL, always ground each example to a concrete cluster/database pair that actually hosts the referenced objects (based on `jupyter-templates/`).
- For curated sample KQL patterns, see `references/` under this coding ability folder.

Prereqs

- Run inside an environment where `xportal` is available.
- You must have access to the target cluster/database.

## Remarks

Interfaces (from `zero-toil/.venv/Lib/site-packages/xportal/kusto.py`)

- `await kusto.query(cluster: str, database: str, query: str, environment: Optional[str] = None) -> KustoQueryResult`
	- `cluster` accepts a short name (e.g. `"icmcluster"`) or full URI (e.g. `"https://icmcluster.kusto.windows.net"`).
	- `environment` (optional) supports: `"Production"`, `"Mooncake"`, `"Fairfax"`, `"USNat"`, `"USSec"`.
	- Write operations are disallowed by the client.
- Return type: `KustoQueryResult`
	- Data members: `Fields: List[str]`, `FieldType: List[str]`, `Data: List[List[Any]]`
	- Helpers: `to_df() -> pandas.DataFrame`, `to_dict() -> dict`, `show(columns: Optional[List[str]] = None) -> None`

Sharable link helper

- `kusto.get_kusto_query_link(cluster: str, database: str, query: str, environment: str = None) -> str`

## Sample Python code

```python
from xportal import kusto

cluster_name = "<cluster_name_or_uri>"  # e.g. "icmcluster.kusto.windows.net"
database_name = "<database_name>"
query = """
<your KQL here>
""".strip()

result = await kusto.query(cluster_name, database_name, query)
df = result.to_df()

df.head(20)

# Sharable link for Kusto Explorer
kusto_link = kusto.get_kusto_query_link(cluster_name, database_name, query)
kusto_link
```
