# Role Instances API patterns

These examples show how to list, filter, and ping role instances for a tenant.

## Example: List all role instances and filter by role type

```python
from xds_client import RoleInstancesApi

tenant_name = "<tenant_name>"  # e.g. "MS-AM5PrdStr04A"

role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant(tenant_name)

all_roles = await role_api.role_instances_get_role_instances()

# Filter to specific role types
csm_roles = [r for r in all_roles if r.role_name and r.role_name.lower() == "csm"]
fe_roles = [r for r in all_roles if r.role_name and r.role_name.lower() == "fe"]
en_roles = [r for r in all_roles if r.role_name and r.role_name.lower() == "en"]
ts_roles = [r for r in all_roles if r.role_name and "tableserver" in (r.role_name or "").lower()]

print(f"CSMs: {len(csm_roles)}, FEs: {len(fe_roles)}, ENs: {len(en_roles)}, TSs: {len(ts_roles)}")

for r in csm_roles:
    print(f"  {r.role_instance_name}  UD={r.upgrade_domain}  FD={r.fault_domain}  Node={r.node_id}")
```

Inspired by:
- jupyter-templates/Xstore/Stream/ZRS/GetBadStreamManagerWithXdsPing.ipynb
- jupyter-templates/Xstore/XTable/DataCorruptionFENodeAnalysis.ipynb

## Example: Ping role instances to check responsiveness

```python
from xds_client import RoleInstancesApi, models

tenant_name = "<tenant_name>"

role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant(tenant_name)

# Get all role instances first
all_roles = await role_api.role_instances_get_role_instances()

# Filter to target roles (e.g., CSMs)
target_roles = [r for r in all_roles if r.role_name and r.role_name.lower() == "csm"]

# Ping them
ping_params = models.PingRequestParams(
    role_instance_names=[r.role_instance_name for r in target_roles],
    request_role_ping=True,
    request_rdma_ping=False,
    request_log_agent_ping=True,
)
ping_results = await role_api.role_instances_ping(ping_params)

# Evaluate results — find unresponsive instances
for p in ping_results:
    status = p.role_status or "Unknown"
    log_status = p.log_agent_status or "Unknown"
    print(f"{p.role_instance_name}: role={status}, log_agent={log_status}, machine={p.machine_name}")

offline = [p for p in ping_results if p.role_status and "unresponsive" in p.role_status.lower()]
print(f"\nOffline instances: {len(offline)}")
```

Inspired by:
- jupyter-templates/Xstore/Stream/ZRS/GetBadStreamManagerWithXdsPing.ipynb
- jupyter-templates/Xstore/Stream/vNext/AutoMitigate/SMEMSyncRaceCondition.ipynb

## Example: Get a single role instance by name

```python
from xds_client import RoleInstancesApi

role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant("<tenant_name>")

instance = await role_api.role_instances_get_role_instance("<role_instance_name>")
print(f"Role: {instance.role_name}, UD: {instance.upgrade_domain}, FD: {instance.fault_domain}")
```

## Example: Get tenant build info

```python
from xds_client import RoleInstancesApi

role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant("<tenant_name>")

build_info = await role_api.role_instances_get_tenant_build_info()
print(build_info)
```

Inspired by:
- jupyter-templates/Xstore/AGC/ClusterTemp.ipynb

## Notes

- `role_instances_get_role_instances()` takes **no parameters** — it returns *all* role instances for the connected tenant.
- The returned `RoleInstance` model includes `role_name`, `role_instance_name`, `upgrade_domain`, `fault_domain`, `node_id`, `physical_tenant_name`.
- Common role types: `CSM`, `FE`, `EN`, `TableServer`, `XStreamServer`, `XFE`.
- `PingRequestParams` must specify which ping types to request (`request_role_ping`, `request_rdma_ping`, `request_log_agent_ping`).
- Ping can be slow for large tenants — consider filtering to specific roles before pinging.
