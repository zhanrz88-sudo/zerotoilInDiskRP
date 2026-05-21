# ADO Build Query — Reference Examples

## Kusto-based build failure detection

Queries the `1es` / `AzureDevOps` Kusto cluster to find failed builds by pipeline name.

### Example: Find recent build failures for a pipeline

```python
from xportal import kusto

definition_name = "<pipeline_definition_name>"

build_query = f'''
cluster('1es.kusto.windows.net').database('AzureDevOps').Build
| where EtlProcessDate > ago(2d)
| where DefinitionName contains "{definition_name}"
| where SourceBranch in ("refs/heads/master") or SourceBranch has ("refs/heads/release/")
| summarize arg_max(EtlProcessDate, *) by SourceBranch
| project Result, DefinitionName, BuildId, SourceBranch, Timestamp=format_datetime(EtlProcessDate, 'MM-dd-yyyy HH:mm:ss'), Data
'''

result = await kusto.query("1es", "AzureDevOps", build_query)
result.show()
```

**Validation**: ✅ Validated — real `await kusto.query("1es", "AzureDevOps", ...)` call.  
**Source**: Inspired by [jupyter-templates/Cosmos Store/Alert Build Failure V2.ipynb](../../jupyter-templates/Cosmos%20Store/Alert%20Build%20Failure%20V2.ipynb)

---

## REST API-based release pipeline queries

Uses `xportal.ado.get_access_token()` to authenticate, then calls ADO release APIs to check deployment status.

### Example: Check latest release deployment status

```python
from xportal import ado
from xportal.utils import RestHelper

access_token = await ado.get_access_token()
headers = {"Authorization": "Bearer " + access_token}

definition_id = <definition_id>
url = f"https://vsrm.dev.azure.com/msazure/One/_apis/release/releases?definitionId={definition_id}&$top=1&queryOrder=descending&api-version=7.1-preview.8"

releases = await RestHelper.fetch_get(url, headers=headers)
for release in releases.get("value", []):
    release_id = release["id"]
    release_name = release["name"]
    # Get deployment environment details
    detail_url = release["url"]
    full_release = await RestHelper.fetch_get(detail_url, headers=headers)
    for env in full_release.get("environments", []):
        print(env.get("name"), env.get("status"))
```

**Validation**: ✅ Validated — real `await ado.get_access_token()` + REST API call pattern.  
**Source**: Inspired by [jupyter-templates/AzureRT/DiskService/BVTRegressions/GetRegions.ipynb](../../jupyter-templates/AzureRT/DiskService/BVTRegressions/GetRegions.ipynb)

---

## ADO SDK-based queries

Uses `XJPLAzureDevopsCredential` for the official `azure-devops` Python SDK.

### Example: List projects using the official SDK

```python
from azure.devops.connection import Connection
from xportal.ado import XJPLAzureDevopsCredential

ORGANIZATION_URL = "https://dev.azure.com/msazure"
connection = Connection(base_url=ORGANIZATION_URL, creds=XJPLAzureDevopsCredential())
core_client = connection.clients.get_core_client()
projects = core_client.get_projects()
for project in projects:
    print(project.name)
```

**Validation**: 🔶 API source validated — signature confirmed from `xportal/ado.py` docstring example. SDK import pattern used in notebooks.  
**Source**: `zero-toil/.venv/Lib/site-packages/xportal/ado.py` (XJPLAzureDevopsCredential docstring); notebook pattern from [jupyter-templates/AzureDirectDrive/XDirectQuality/Weekly-ShiftReport.ipynb](../../jupyter-templates/AzureDirectDrive/XDirectQuality/Weekly-ShiftReport.ipynb)

---

## Referenced but not validated

The following ADO operations are referenced in the TSG but no notebook example was found that calls them directly:

| Operation | Context | Notes |
|---|---|---|
| Query build runs by `definitionId` via REST `_apis/build/builds` | TSG needs to check if a build ran in the last 3 hours for a specific pipeline definition ID | The REST pattern is standard ADO API; authentication is validated via `ado.get_access_token()`. The Kusto approach (`1es`/`AzureDevOps`/`Build` table) is a validated alternative. |
| Map process name to pipeline `definitionId` | TSG needs to resolve XI service names to ADO pipeline IDs | No programmatic mapping found — the TSG relies on a static lookup table. |
