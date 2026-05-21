---
name: diskrp-icm-full-stack
description: "Full-stack DiskRP ICM incident handling: Kusto triage, root cause analysis, HTML commenting, custom field updates, mitigation, and resolution. USE FOR: triage DiskRP incident, investigate disk incident, comment on ICM, mitigate incident, resolve incident, post RCA, DiskRP root cause, disk service on-call."
---

# DiskRP ICM Full-Stack Skill

End-to-end workflow for triaging, investigating, commenting, mitigating, and resolving DiskRP ICM incidents using zerotoil (`xportal.icm` + `xportal.kusto`).

## When to apply this skill

- When asked to **triage** a DiskRP / Disk Service incident
- When asked to **comment**, **mitigate**, or **resolve** an ICM incident
- When asked to **post an RCA** to an incident
- When asked to **investigate** disk failures using Kusto
- Any ICM incident owned by `AZURERT\DiskService` (team ID: 28322)

## Prerequisites

- `.venv` activated (contains `xportal` with `icm` and `kusto` modules)
- Authenticated to ICM and Kusto

## Full-Stack Workflow

### Step 1: Fetch Incident

```python
from xportal import icm

incident = await icm.get_incident(<incident_id>, should_get_description=True)
print(incident.Title, incident.Severity, incident.Status, incident.OwningContactAlias)
```

Key fields: `Title`, `Severity`, `Status`, `Tags`, `OwningContactAlias`, `CreateDate`, `Summary`, `MitigationData`, `ResolutionData`, `CustomFieldGroups`.

### Step 2: Kusto Triage

All queries target cluster **`Disks`**, database **`Disks`**.

#### Phase 1: Error Trend (DiskManagerApiQoSEvent)

```kql
DiskManagerApiQoSEvent
| where PreciseTimeStamp between (datetime('<START>') .. datetime('<END>'))
| where region =~ '<REGION>'
| where resultCode != ''
| summarize Count=count() by resultCode, exceptionType, operationName
| order by Count desc
```

Hourly error rate:

```kql
DiskManagerApiQoSEvent
| where PreciseTimeStamp between (datetime('<START>') .. datetime('<END>'))
| where region =~ '<REGION>'
| summarize Total=count(), Errors=countif(resultCode != '') by bin(PreciseTimeStamp, 1h)
| extend ErrorRate=round(todouble(Errors)/todouble(Total)*100, 2)
| order by PreciseTimeStamp asc
```

Get a sample operationId for tracing:

```kql
DiskManagerApiQoSEvent
| where PreciseTimeStamp between (datetime('<START>') .. datetime('<END>'))
| where region =~ '<REGION>'
| where resultCode == '<TARGET_RESULT_CODE>'
| project PreciseTimeStamp, subscriptionId, operationId, resultCode, exceptionType,
    errorDetails=substring(errorDetails, 0, 600)
| take 3
```

#### Phase 2: Root Cause Trace (DiskManagerContextActivityEvent)

Use `operationId` from Phase 1 as `activityId` in ContextActivity:

```kql
DiskManagerContextActivityEvent
| where PreciseTimeStamp between (datetime('<TIME>') - 5m .. datetime('<TIME>') + 5m)
| where activityId == '<OPERATION_ID>'
| project PreciseTimeStamp, msg=substring(message, 0, 500)
| order by PreciseTimeStamp asc
```

Search for specific error patterns:

```kql
DiskManagerContextActivityEvent
| where PreciseTimeStamp between (datetime('<START>') .. datetime('<END>'))
| where message has '<ERROR_KEYWORD>'
| summarize Count=count() by bin(PreciseTimeStamp, 1h)
| order by PreciseTimeStamp asc
```

**Key schema notes:**
- `DiskManagerApiQoSEvent` uses `region` column
- `DiskManagerContextActivityEvent` does NOT have a `region` column — filter by time + activityId or message content
- `DiskRPExternalComponentQoSEvent` uses `RPTenant` (not `region`), `componentName` (not `component`)
- `operationId` in ApiQoSEvent == `activityId` in ContextActivityEvent

#### Phase 3: External Components (if needed)

```kql
DiskRPExternalComponentQoSEvent
| where PreciseTimeStamp between (datetime('<START>') .. datetime('<END>'))
| where RPTenant has '<REGION_OR_TENANT>'
| where componentName == '<COMPONENT>'
| where operationResult == 'UnexpectedFailure'
| summarize Count=count() by operationName, resultCode
| order by Count desc
```

### Step 3: Post Comment (HTML)

```python
await incident.add_description("<h3>Title</h3><p>Content</p>", is_html=True)
```

**Critical HTML rules for ICM:**
- Do NOT use `&rarr;`, `&mdash;`, `&ndash;` or other HTML entities — they render as `?` in ICM
- Use plain ASCII alternatives: `->` for arrows, `--` for dashes
- Safe tags: `<h2>`, `<h3>`, `<h4>`, `<p>`, `<b>`, `<i>`, `<code>`, `<pre>`, `<table>`, `<ul>`, `<ol>`, `<li>`, `<br>`, `<hr>`
- For code blocks, use `<pre>...</pre>`
- For inline code, use `<code>...</code>`
- Build HTML with Python string concatenation (parenthesized), NOT triple-quoted f-strings (which break in piped scripts)

### Step 4: Update Custom Fields

Inspect available fields first:

```python
for g in incident.CustomFieldGroups:
    group_type = g.get('GroupType')
    container_id = g.get('ContainerId')
    public_id = g.get('PublicId')
    for f in g.get('CustomFields', []):
        name = f.get('<Name>k__BackingField', f.get('Name', ''))
        print(f"  {group_type}/{container_id}: {name}")
```

Update Tenant-level fields (MitigationSteps, Recommendation):

```python
await incident.update_custom_fields('Tenant', [
    {"Name": "MitigationSteps", "Type": "RichText", "Value": "<b>Mitigation HTML here</b>"}
], public_id="f1305a04-595b-45b4-bb4c-3fcdc18f6748", container_id="10064")

await incident.update_custom_fields('Tenant', [
    {"Name": "Recommendation", "Type": "RichText", "Value": "<b>Solution HTML here</b>"}
], public_id="f1305a04-595b-45b4-bb4c-3fcdc18f6748", container_id="10064")
```

Update RootCause field (via UpdateIncident API):

```python
from xportal.icm import RestHelper, get_endpoint
from urllib.parse import urljoin
import json

body = json.dumps({"RootCause": "Root cause text here"}, default=str)
await RestHelper.fetch_post(
    urljoin(get_endpoint(), f"/api/v1/Icm/UpdateIncident?incidentId={incident.Id}"),
    body, response_type=None,
)
```

**Note:** `HowFixed` is NOT a valid field name for the UpdateIncident API — it returns 400. The `RootCause` field works. For solution/fix details, use the `Recommendation` custom field or the description comment.

### Step 5: Mitigate

```python
await incident.mitigate("Mitigation reason text here")
```

This sets `MitigationData` and changes status to Mitigated.

### Step 6: Resolve

```python
await incident.resolve("Resolution reason text here")
```

**Note:** The `resolve()` API sends `{"Description": {"Text": reason}}` — it adds a description entry but does NOT populate the ResolutionData reason field directly. Always set `RootCause` via UpdateIncident before resolving.

To re-resolve (e.g., to fix fields): activate first, update fields, then mitigate + resolve:

```python
await incident.activate("Re-activating to update fields.")
# ... update fields ...
await incident.mitigate("Mitigation reason")
incident = await icm.get_incident(<id>)  # re-fetch after mitigate
await incident.resolve("Resolution reason")
```

## Hard Rules

- **ALWAYS pass `is_html=True`** when calling `incident.add_description()`. Without it, `RenderType` defaults to `Plaintext` and HTML tags render as raw text in ICM. Every comment we post uses HTML formatting.
- **Never use `&rarr;`, `&mdash;`, `&ndash;`** HTML entities — they render as `?` in ICM. Use `->` and `--` instead.
- **ICM descriptions cannot be deleted** — post a new comment marked as superseding the old one.

## DiskRP-Specific Reference

| Item | Value |
|------|-------|
| Team | AzureRT/Disk Service |
| Team ID | 28322 |
| Kusto Cluster | Disks |
| Kusto Database | Disks |
| EUAP Regions | eastus2euap, centraluseuap (canary -- lower priority) |
| Tenant custom fields | ContainerId=10064, PublicId=f1305a04-595b-45b4-bb4c-3fcdc18f6748 |
| Key tables | DiskManagerApiQoSEvent, DiskManagerContextActivityEvent, DiskRPExternalComponentQoSEvent |
| DisksBI tables | Disk, StorageAccount, DiskEncryptionSet, CorObject (cluster: disksbi, db: DisksBI) |

## Common Error Patterns

| DiskRP resultCode | Typical Root Cause |
|---|---|
| StorageFailure/Timeout | DirectDrive or storage backend timeout; check ContextActivity for underlying error |
| DiskServiceInternalError | DirectDriveClientException — often quota, capacity, or transient storage issue |
| NotFound | Normal — disk/resource already deleted |
| OperationNotAllowed/TooManyRequestsReceived | Throttling — usually self-resolving |

## Python Script Execution Pattern

When running zerotoil Python via piped scripts on Windows:

```powershell
$pyScript = @'
import asyncio
from xportal import icm

async def main():
    # ... your code ...
    pass

asyncio.run(main())
'@
$pyScript | & "C:\git\XScript-Templates\zero-toil\.venv\Scripts\python.exe" -
```

This avoids triple-quote escaping issues with inline `-c` execution.
