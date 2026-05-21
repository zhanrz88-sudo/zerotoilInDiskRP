---
name: XDS API Call
description: Call XDS REST APIs via the xds_client package to query role instances, upgrade state, management role, XTable reads, and other tenant-scoped operations. For XDS log search, see xds-log-search.
---

# Coding Ability: xds-api-call

## Description

Calls XDS (XStore Deployment Service) REST APIs using the auto-generated `xds_client` package. XDS is the control-plane service for XStore tenants — it exposes APIs for role instance management, upgrade/deployment state, dynamic config, XTable/XStream data access, and more.

- Intended for code generation building blocks.
- **Read-only by default.** Some APIs (restart, quarantine, config rollout) are mutating — call those out explicitly and gate behind confirmation.
- Every API call is **tenant-scoped**: you must first connect the `ApiClient` to a tenant before calling any API method.
- The `xds_client` package is Swagger-generated; each API class follows the same pattern: instantiate → connect → call methods.
- For curated usage patterns grouped by API family, see `references/` under this coding ability folder.

Key concepts

- **ApiClient**: The HTTP client that handles auth and routing. Must be connected to a tenant via `await api_client.connect_tenant(tenant_name)` before any call.
- **API classes**: One class per API family (e.g., `RoleInstancesApi`, `UpgradeStateApi`, `ManagementRoleApi`). Each wraps a set of related REST endpoints.
- **Models**: Typed request/response objects under `xds_client.models` (e.g., `RoleInstance`, `UpgradeState`, `PingRequestParams`, `PingResponse`).
- **`xstore.xds`**: A higher-level helper module that wraps log-search and resource-info calls. Separate from `xds_client`. For XDS log search, see the dedicated `xds-log-search` coding ability.

Prereqs

- Run inside an environment where `xds_client` and `xstore` are available (XPortal Jupyter / XScript runtime).
- The managed service identity must have XDS access for the target tenant.

## Source code references

When mapping PowerShell cmdlets to Python API calls, consult the XDS source code in the `Storage-XStore` repo (`project: One`, `repositoryId: Storage-XStore`):

- **PowerShell cmdlets** (XTable): [`src/XTable/Tools/XDiagCmdLet/XdsXtable.cs`](https://msazure.visualstudio.com/One/_git/Storage-XStore?path=/src/XTable/Tools/XDiagCmdLet/XdsXtable.cs&version=GBmain)
- **REST API controllers** (XTable): [`src/XDiagnostics/Api/Controllers/XTable/Lib/XTableController.cs`](https://msazure.visualstudio.com/One/_git/Storage-XStore?path=/src/XDiagnostics/Api/Controllers/XTable/Lib/XTableController.cs&version=GBmain)

Use ADO MCP `ado-mcp-msazure-org-repo_file` with `action: get_content` to fetch these files programmatically.

## Remarks

### Connection pattern (from `xds_client.ApiClient`)

```python
from xds_client import ApiClient
client = ApiClient()
await client.connect_tenant(tenant_name: str, environment: str = None)
```

- `tenant_name`: Full tenant name (e.g., `"MS-AM5PrdStr04A"`).
- `environment`: Optional. `"Production"` (default), `"Mooncake"`, `"Fairfax"`, `"USNat"`, `"USSec"`.
- All API classes accept an `api_client` parameter; if omitted they create a default `ApiClient()`.

### Available API classes (from `xds_client.__init__`)

| API Class | Purpose | Key read-only methods |
|---|---|---|
| `RoleInstancesApi` | Role instance listing, ping, build info | `role_instances_get_role_instances()`, `role_instances_ping(params)`, `role_instances_get_role_instance(name)` |
| `UpgradeStateApi` | Deployment/upgrade state, domain readiness | `upgrade_state_get_upgrade_state()`, `upgrade_state_is_upgrade_in_progress()`, `upgrade_state_get_role_quorums()` |
| `ManagementRoleApi` | Node repair, quarantine, safety checks | `management_role_get_mr_role_instance_states()`, `management_role_get_quarantine_status()` |
| `TenantApi` | Tenant metadata | (tenant-level queries) |
| `DynamicConfigApi` | Dynamic config settings | (config reads) |
| `ConfigRolloutApi` | Config rollout status | (rollout queries) |
| `XTableApi` | XTable data reads, partition stats | `x_table_read_table(args)`, `x_table_get_partitions_stats(page_number, if_modified_since, ...)`, `x_table_get_partition_stats(partition_name, if_modified_since)`, `x_table_get_tables()` |
| `XStreamApi` | XStream data reads | (stream queries) |
| `XComputeApi` | XCompute job management | (job queries) |
| `AccountSettingsApi` | Account-level settings | (account queries) |

### Key models (from `xds_client.models`)

**`RoleInstance`** — returned by `role_instances_get_role_instances()`

| Field | Type | Description |
|---|---|---|
| `role_name` | `str` | Role type (e.g., `"CSM"`, `"FE"`, `"EN"`, `"TableServer"`) |
| `role_instance_name` | `str` | Instance name (e.g., `"csm_in_5"`) |
| `address` | `str` | IP address |
| `upgrade_domain` | `str` | Upgrade domain |
| `fault_domain` | `str` | Fault domain |
| `neighborhood` | `str` | Neighborhood |
| `fabric_fault_domain` | `str` | Fabric fault domain |
| `node_id` | `str` | Node GUID |
| `physical_tenant_name` | `str` | Physical tenant name |

**`PingRequestParams`** — input to `role_instances_ping()`

| Field | Type | Description |
|---|---|---|
| `role_instance_names` | `list[str]` | Role instance names to ping |
| `request_role_ping` | `bool` | Ping the role process |
| `request_rdma_ping` | `bool` | Ping RDMA |
| `request_log_agent_ping` | `bool` | Ping log agent |

**`PingResponse`** — returned by `role_instances_ping()`

| Field | Type | Description |
|---|---|---|
| `role_instance_name` | `str` | Instance name |
| `role_status` | `str` | Role responsiveness (e.g., `"Responsive"`, `"Unresponsive"`) |
| `log_agent_status` | `str` | Log agent status |
| `role_instance_start_time` | `datetime` | When the role instance started |
| `system_up_time` | `datetime` | System uptime |
| `machine_name` | `str` | Machine hostname |
| `remarks` | `str` | Additional remarks |

**`UpgradeState`** — returned by `upgrade_state_get_upgrade_state()`

| Field | Type | Description |
|---|---|---|
| `upgrade_status` | `str` | Status (e.g., `"Upgrade In Progress"`, `"No Upgrade"`) |
| `upgrade_client` | `str` | Client that initiated the upgrade |
| `upgrade_id` | `str` | Upgrade identifier |
| `upgrade_description` | `str` | Description of the upgrade |
| `current_domain_id` | `str` | Current domain being upgraded |
| `current_domain_type` | `str` | Domain type (`"UD"`, `"FD"`) |
| `current_task_name` | `str` | Current upgrade task |
| `current_task_status` | `str` | Task status |
| `current_task_start_time` | `str` | When the current task started |
| `current_domain_start_time` | `str` | When the current domain upgrade started |
| `estimated_completion_time` | `str` | Estimated completion |
| `domain_id_sequence` | `str` | Sequence of domains to upgrade |
| `batch_count` | `str` | Total batches |
| `current_batch_id` | `str` | Current batch |
| `is_lazy_replication_in_progress` | `bool` | Whether lazy repl is active |

### Higher-level helper: `xstore.common.xds.XdsApiClient`

A convenience wrapper that auto-connects and exposes XTable reads:

```python
from xstore.common.xds import XdsApiClient
client = XdsApiClient(tenant="<tenant_name>", environment="Production")
await client.connect()
result = await client.read_table("<table_name>", key_low=[...], key_high=[...])
```

## Sample Python code

```python
from xds_client import RoleInstancesApi, UpgradeStateApi, ApiClient, models

tenant_name = "<tenant_name>"  # e.g. "MS-AM5PrdStr04A"

# --- Get all role instances ---
role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant(tenant_name)
all_roles = await role_api.role_instances_get_role_instances()

# Filter to CSMs
csm_roles = [r for r in all_roles if r.role_name and r.role_name.lower() == "csm"]
for r in csm_roles:
    print(f"{r.role_instance_name}  UD={r.upgrade_domain}  FD={r.fault_domain}  Node={r.node_id}")

# --- Ping CSM instances ---
ping_params = models.PingRequestParams(
    role_instance_names=[r.role_instance_name for r in csm_roles],
    request_role_ping=True,
    request_rdma_ping=False,
    request_log_agent_ping=True,
)
ping_results = await role_api.role_instances_ping(ping_params)
for p in ping_results:
    print(f"{p.role_instance_name}: role={p.role_status}, log_agent={p.log_agent_status}")

# --- Get upgrade/deployment state ---
upgrade_api = UpgradeStateApi()
await upgrade_api.api_client.connect_tenant(tenant_name)
state = await upgrade_api.upgrade_state_get_upgrade_state()
print(f"Upgrade status: {state.upgrade_status}")
print(f"Current domain: {state.current_domain_type} {state.current_domain_id}")
print(f"Task: {state.current_task_name} ({state.current_task_status})")
```
