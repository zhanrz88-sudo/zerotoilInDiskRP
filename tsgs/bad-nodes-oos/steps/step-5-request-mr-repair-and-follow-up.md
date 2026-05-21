# Step 5 — Request MR repair and create follow-up tasks

> **Parent TSG**: [bad-nodes-oos](../bad-nodes-oos.md)
> **Maps to**: `_step_5_request_mr_repair_and_follow_up()` method

## Purpose
After mitigating the bad role instance (via restart or OOS), request MR (Machine Repair) if hardware issues are suspected, and file a follow-up bug with all collected diagnostic artifacts for root cause investigation.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `role_instance_names` | `list[str]` | TSG input |
| `incident_id` | `int` | TSG input |
| `is_zrs_tenant` | `bool` | TSG input |
| `oos_method` | `str` | From Step 4 — which OOS approach was used |
| `diagnostic_links` | `list[str]` | From Step 2 — log collector links, DGrep links |
| `hardware_suspected` | `bool` | DRI judgment — whether hardware issues are suspected |

## Outputs
| Field | Type | Description |
|---|---|---|
| `mr_requested` | `bool` | Whether MR repair was requested |
| `mr_repair_action` | `str` | Repair action type (e.g., `RMA`) |
| `follow_up_bug_id` | `str` | Bug ID filed under `One\XStore\XFE` |

## Processing Logic

### 5a. Request MR Repair (if hardware suspected)

#### Preferred: Geneva Action

Execute `RequestRepairActionFromMRDelegated`:

```python
from xportal import acis

# NOTE: Mutating — requires SAW/dSTS auth
params = [
    "<tenant_name>",          # For ZRS: use virtual ZRS tenant
    "<role_instance_id>",     # One role instance. For ZRS: include physical tenant prefix
    "RMA",                    # Requested Repair Action
    "<repair_reason>",        # Describe the issues
    "0",                      # Repair Fault Code
]

response = await acis.submit(
    "Xstore",
    "RequestRepairActionFromMRDelegated",
    params,
    endpoint="Production",
)
action_id = response["id"]
result = await acis.get_result("Xstore", action_id, wait_for_completion=True)
```

#### Fallback: XDS

If Geneva Action fails, use XDS:
1. XDS > Role Summary > select the role instance
2. Click **Request MR Repair**
3. Fill in:
   - Fault Reason: describe issues
   - Repair Type: `RMA`
   - Fault Code: `0`

### 5b. Create Follow-up Tasks

1. **Download logs** from XDS via Log File Explorer:
   - Role instance log files
   - `.etl` trace files (from CPU trace in Step 2)

2. **Search for crash dump** in Azure Watson.

3. **File a bug** under `One\XStore\XFE` with links to:
   - Log files (from Log File Explorer)
   - Trace .etl files
   - Watson crash dump (if found)
   - ICM incident `<incident_id>`
   - DGrep query link (from Step 2)
   - Actions taken summary

```python
from xportal import icm

incident = await icm.get_incident(<incident_id>)

summary = f"""
Bad Node Mitigation Summary:
- Tenant: <tenant_name>
- Role Instances: {', '.join(role_instance_names)}
- OOS Method Used: {oos_method}
- MR Requested: {mr_requested}
- Follow-up Bug: {follow_up_bug_id}

Diagnostic Links:
{chr(10).join(diagnostic_links)}
"""
await incident.add_description(summary)
```

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY:
  - geneva-action-call (RequestRepairActionFromMRDelegated — mutating, requires SAW/dSTS)
  - xds-api-call (ManagementRoleApi.management_role_request_repair — mutating fallback)
  - xds-log-search (generate_log_search_link — generate log download links)
  - icm-get-incident (add_description — post summary to ICM)
AUTOMATABLE: Partially
  - 5a (MR Repair): Mutating — automation can prepare params and generate GA portal link
  - 5b (Download logs): Partially — xds-log-search can generate links; actual download may require XDS UX
  - 5b (Watson search): Manual — no known programmatic API for Azure Watson crash dump search
  - 5b (File bug): Manual — ADO work item creation could be automated but is not in current coding abilities
MANUAL_FALLBACK: Execute RequestRepairActionFromMRDelegated GA on SAW. Use XDS Log File Explorer to download logs. Search Azure Watson manually. File bug in ADO under One\XStore\XFE.
```

## Open Questions
| # | Question |
|---|---|
| 1 | What are the exact positional parameters for `RequestRepairActionFromMRDelegated`? Is the order: tenant, role instance, repair action, reason, fault code? |
| 2 | For ZRS tenants, the source says "use virtual ZRS tenant" for MR but "physical tenant" for quarantine — what's the mapping function between physical and virtual ZRS tenant names? |
| 3 | Is there an API to search Azure Watson for crash dumps programmatically? |
| 4 | Can ADO work item creation be automated via `xportal` or another available module? This would allow automated bug filing under `One\XStore\XFE`. |
| 5 | ~~Is there a way to programmatically download logs from XDS Log File Explorer?~~ **Resolved**: The `xds-log-search` coding ability provides `search_log` and `generate_log_search_link` — but these search logs, they don't download the actual log files. Download may still require XDS UX. |
