# Node Recovery Geneva Actions

**Status**: These operation IDs are referenced in jupyter-templates but **no notebook was found that directly calls `acis.execute()` or `acis.submit()` with these operations**. The GenevaAction.ipynb notebook only generates hyperlinks to the Geneva Actions UI — it does not invoke them programmatically.

The operation IDs below are confirmed to exist (referenced in multiple templates) but the actual `acis.execute()` call pattern for node recovery has not been validated in any existing notebook.

## Confirmed operation IDs (from notebook references, not direct acis calls)

| OperationId | Extension | Breadcrumb | Source |
|---|---|---|---|
| `ResetNodeHealthWithSafetyChecksCrossServiceDelegated` | `Xstore` | `Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Reset Node Health` | jupyter-templates/Xstore/XSSE/XCopilot/XSSEAgentInstructions.ipynb |
| `PowerNodeWithSafetyChecksDelegated` | `Xstore` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Power Node With Safety Checks And Delegated Auth` | jupyter-templates/Xstore/XSSE/XCopilot/XSSEAgentInstructions.ipynb |
| `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated` | `Xstore` | `Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Put Node Into MOS` | jupyter-templates/Xstore/XSSE/XCopilot/GenevaAction.ipynb |

## Example: Generate Geneva Action hyperlink (validated from real notebook)

This is the actual pattern found in notebooks — generating a URL to the Geneva Actions portal, not calling `acis.execute()` directly.

```python
from urllib.parse import urlencode
import json

async def generate_geneva_action_hyperlink(operation_id, breadcrumb, cluster_name="", tenant_name="", node_id="", incident_id=""):
    parts = [part.strip() for part in breadcrumb.split('>')]
    extension = parts[0]
    group = parts[1]
    operation_name = parts[2]

    params = {
        "tenantname": tenant_name,
        "nodeid": node_id,
        "incidentid": incident_id,
        "clustername": cluster_name,
    }

    query_params = {
        "page": "actions",
        "acisEndpoint": "Public",
        "extension": extension,
        "group": group,
        "operationId": operation_id,
        "operationName": operation_name,
        "params": json.dumps(params),
        "actionEndpoint": "Production",
    }

    base_url = "https://portal.microsoftgeneva.com/?"
    return base_url + urlencode(query_params)

# Usage
link = await generate_geneva_action_hyperlink(
    "PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated",
    "Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Put Node Into MOS",
    node_id="<node_id>",
    incident_id="<incident_id>",
)
```

Source: jupyter-templates/Xstore/XSSE/XCopilot/GenevaAction.ipynb

## Open gap

No existing notebook calls `acis.execute()` or `acis.submit()` directly for node recovery operations (`ResetNodeHealth`, `PowerNode`, `PutNodeIntoMOS`). The `xportal.acis` API supports it (confirmed from `.venv` source code), but the exact parameter list and order for these specific operations has not been validated via a real notebook execution. The parameter tables in the TSG docs are from documentation, not from verified code.
