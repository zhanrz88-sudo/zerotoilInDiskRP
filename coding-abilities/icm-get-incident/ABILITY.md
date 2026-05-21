---
name: ICM - Get and update incident
description: Fetch an ICM incident entity by id, and optionally update severity, tags, descriptions, owner, or lifecycle state.
---

# Coding Ability: icm-get-incident

## Description
Fetches an ICM incident entity by incident id using the `xportal.icm` client. The returned `Incident` object also supports update operations (severity, tags, descriptions, owner, TSG link, mitigate, resolve, transfer, acknowledge).

- Intended for code generation building blocks.
- Read operations are safe by default.
- **Update operations are mutating** — use only when explicitly intended. Each update call also adds a description entry to the incident's discussion thread.

Additional module-level functions

- `await icm.search_incidents(filter, top=100, skip=None) -> List[Incident]` — Search incidents by OData filter.
- `await icm.create_incident(title, severity, routing_id, summary=None, ...) -> IncidentCreationResult` — Create a new incident.
- `await icm.get_current_oncall_of_team(team_id) -> dict` — Get current on-call for a team.

Prereqs

- Run inside an environment where `xportal` is available (XPortal Jupyter / XScript runtime).
- You must already be authenticated/authorized to read/write ICM incidents.

## Remarks

Interface (from `zero-toil/.venv/Lib/site-packages/xportal/icm.py`)

### Fetch incident

- `await icm.get_incident(incident_id: int, should_get_description: bool = True) -> Incident`
- Return type: `Incident`
	- Common fields (subset): `Id: int`, `Title: str`, `Severity: int`, `Status: str`, `CreateDate: datetime`, `ModifiedDate: datetime`, `Tags: List[str]`, `OwningContactAlias: str`, `MonitorId: str`, `Summary: str`
	- If `should_get_description=True`, `Incident.Descriptions` is populated (type: `List[IncidentDescription]`).
- `IncidentDescription` fields (subset): `Text: Optional[str]`, `ChangedBy: Optional[str]`, `Date: Optional[datetime]`, `RenderType: Optional[str]`.

### Read operations on Incident

- `await incident.get_descriptions() -> List[IncidentDescription]`
- `await incident.download_incident_attachments() -> List[str]`

### Update operations on Incident (mutating)

- `await incident.update_severity(severity: int)` — Update severity (0–4).
- `await incident.update_tags(tags: List[str])` — Replace incident tags.
- `await incident.update_title(title: str)` — Update title.
- `await incident.update_summary(summary: str)` — Update summary.
- `await incident.update_owner(alias: str)` — Change owning contact.
- `await incident.update_tsg(tsg: str)` — Set TSG link.
- `await incident.add_description(text: str, is_html: bool = False)` — Add comment to discussion.
- `await incident.update_custom_fields(group_type: str, custom_fields: List[Any], public_id: str = "0000...", container_id: Optional[str] = None)` — Update custom fields.

### Lifecycle operations on Incident (mutating)

- `await incident.acknowledge(alias: str = "xdashdev")` — Acknowledge incident.
- `await incident.mitigate(reason: Optional[str] = None)` — Mitigate incident.
- `await incident.activate(reason: Optional[str] = None)` — Activate incident.
- `await incident.resolve(reason: Optional[str] = None)` — Resolve incident.
- `await incident.transfer(tenant: str, team: str, reason: Optional[str] = None)` — Transfer to another team.
- `await incident.link_incident(related_incident_id: int, relationship_type: str = "Related")` — Link to another incident.

### Search and create

- `await icm.search_incidents(filter: str, top: int = 100, skip: int = None) -> List[Incident]`
  - `filter`: OData filter string (e.g., `"OwningTenantId eq 'xxx' and Status eq 'Active' and Severity eq 1"`)
- `await icm.create_incident(title: str, severity: int, routing_id: str, summary: Optional[str] = None, ...) -> IncidentCreationResult`
  - Returns: `IncidentCreationResult` with `.incident_id: int` and `.status: str`

## Sample Python code

### Read incident

```python
from xportal import icm

incident_id = <incident_id>
incident = await icm.get_incident(int(incident_id))

print(incident.Title)
print(incident.Severity)
print(incident.Status)
```

### Add a description comment

```python
from xportal import icm

incident = await icm.get_incident(<incident_id>)
await incident.add_description("Automation analysis: crash caused by smoke test failure (RunKustoAccessProductionTest). See DGrep link for details.")
```

### Update severity

```python
from xportal import icm

incident = await icm.get_incident(<incident_id>)
await incident.update_severity(2)
```

### Search for active incidents

```python
from xportal import icm

incidents = await icm.search_incidents(
    "OwningTenantId eq '<tenant_id>' and Status eq 'Active' and Severity le 2"
)
for inc in incidents:
    print(inc.Id, inc.Title, inc.Severity)
```
