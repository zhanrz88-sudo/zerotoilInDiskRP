---
name: ADO - Query build pipelines
description: Query Azure DevOps build pipeline runs and release status via xportal.ado and Kusto.
---

# Coding Ability: ado-build-query

## Description

Queries Azure DevOps (ADO) build pipeline runs and release deployment status using two complementary approaches:

1. **Kusto-based** (preferred for bulk/historical queries): Query the `1es` cluster's `AzureDevOps` database for build results by definition name, time range, and branch.
2. **REST API-based** (for release pipelines and real-time status): Use `xportal.ado.get_access_token()` to authenticate, then call ADO REST APIs directly for build/release details.

- Read-only by default.
- No secrets required — `xportal.ado` handles authentication automatically (device flow in browser, service principal in automation).
- Time-bound queries recommended (e.g., last 3 hours / 2 days).

Prereqs

- Run inside an environment where `xportal` is available (XPortal Jupyter / XScript runtime).
- For Kusto-based queries: `kusto-query` coding ability (`xportal.kusto.query`).
- For REST API-based queries: `xportal.ado.get_access_token()`.

## Remarks

### Approach 1: Kusto-based build queries

Interface (from `zero-toil/.venv/Lib/site-packages/xportal/kusto.py` — same as `kusto-query` coding ability)

- `await kusto.query(cluster: str, database: str, query_string: str, environment: Optional[str] = None) -> KustoQueryResult`

Key Kusto cluster/database for ADO builds

| Cluster | Database | Content |
|---|---|---|
| `1es` | `AzureDevOps` | Build results, pipeline definitions, source branches |

Key table: `Build`

| Column | Type | Description |
|---|---|---|
| `DefinitionName` | `string` | Pipeline definition name |
| `DefinitionId` | `int` | Pipeline definition ID |
| `BuildId` | `int` | Build run ID |
| `Result` | `string` | Build result (`succeeded`, `failed`, `canceled`, `partiallySucceeded`) |
| `SourceBranch` | `string` | Source branch (e.g., `refs/heads/main`) |
| `EtlProcessDate` | `datetime` | Build timestamp |
| `Data` | `dynamic` | Full build JSON payload |

### Approach 2: REST API-based queries

Interface (from `zero-toil/.venv/Lib/site-packages/xportal/ado.py`)

- `await ado.get_access_token() -> str` — Returns a Bearer token valid for 60 minutes.
- `ado.get_access_token_nowait() -> str` — Synchronous version.
- `ado.XJPLAzureDevopsCredential()` — Credential class for the official `azure-devops` Python SDK.

ADO REST API patterns (use with Bearer token from `get_access_token()`)

| API | URL Pattern | Purpose |
|---|---|---|
| List builds | `https://dev.azure.com/{org}/{project}/_apis/build/builds?definitions={definitionId}&$top={N}&api-version=7.1` | Get recent builds for a pipeline |
| List releases | `https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases?definitionId={defId}&$top={N}&queryOrder=descending&api-version=7.1-preview.8` | Get recent releases |

### Additional helper functions

- `await ado.get_item_content(project, repo, branch, item_path, is_folder=False, recursionLevel="OneLevel") -> Any` — Get file/folder content from ADO Git repo.
- `await ado.get_commits(project, repo, branch, item_path=None, author=None, from_time=None, to_time=None, skip=None, top=None, include_work_item=False) -> list` — Get commits from ADO Git repo.

## Sample Python code

### Approach 1: Query build status via Kusto

```python
from xportal import kusto

definition_name = "<pipeline_definition_name>"  # e.g., "AutoAnalysis-Official"

build_query = f'''
cluster('1es.kusto.windows.net').database('AzureDevOps').Build
| where EtlProcessDate > ago(3h)
| where DefinitionName contains "{definition_name}"
| summarize arg_max(EtlProcessDate, *) by SourceBranch
| project Result, DefinitionName, BuildId, SourceBranch, Timestamp=format_datetime(EtlProcessDate, 'MM-dd-yyyy HH:mm:ss')
| take 10
'''

result = await kusto.query("1es", "AzureDevOps", build_query)
result.show()
```

### Approach 2: Query release status via REST API

```python
from xportal import ado
from xportal.utils import RestHelper

access_token = await ado.get_access_token()
headers = {"Authorization": "Bearer " + access_token}

definition_id = <definition_id>  # e.g., 395813
url = f"https://vsrm.dev.azure.com/msazure/One/_apis/release/releases?definitionId={definition_id}&$top=5&queryOrder=descending&api-version=7.1-preview.8"

releases = await RestHelper.fetch_get(url, headers=headers)
for release in releases.get("value", []):
    print(release["id"], release["name"], release["status"])
```

### Approach 3: Check recent commits in a repo

```python
import datetime
from xportal import ado

commits = await ado.get_commits(
    project="One",
    repo="<repo_name>",
    branch="main",
    from_time=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3),
    to_time=datetime.datetime.now(datetime.timezone.utc),
    top=10,
)

for commit in commits:
    print(commit.get("commitId", "")[:8], commit.get("comment", ""), commit.get("author", {}).get("date", ""))
```
