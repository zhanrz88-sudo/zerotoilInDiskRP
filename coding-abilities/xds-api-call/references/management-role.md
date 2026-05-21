# Management Role API patterns

These examples show how to query node health, quarantine status, repair history, and safety checks via the ManagementRoleApi.

## Example: Get MR role instance states

```python
from xds_client import ManagementRoleApi

tenant_name = "<tenant_name>"

mr_api = ManagementRoleApi()
await mr_api.api_client.connect_tenant(tenant_name)

states = await mr_api.management_role_get_mr_role_instance_states()
for s in (states or []):
    print(s)
```

Inspired by:
- jupyter-templates/Xstore/Stream/ZRS/GetBadStreamManagerWithXdsPing.ipynb

## Example: Get quarantine status

```python
from xds_client import ManagementRoleApi

mr_api = ManagementRoleApi()
await mr_api.api_client.connect_tenant("<tenant_name>")

quarantine = await mr_api.management_role_get_quarantine_status()
print(quarantine)
```

## Example: Get node repair history

```python
from xds_client import ManagementRoleApi

mr_api = ManagementRoleApi()
await mr_api.api_client.connect_tenant("<tenant_name>")

history = await mr_api.management_role_get_mr_node_repair_history()
for entry in (history or []):
    print(entry)
```

## Example: Get MR fabric jobs

```python
from xds_client import ManagementRoleApi

mr_api = ManagementRoleApi()
await mr_api.api_client.connect_tenant("<tenant_name>")

jobs = await mr_api.management_role_get_mr_fabric_jobs()
for job in (jobs or []):
    print(job)
```

## Example: Check if MR is enabled

```python
from xds_client import ManagementRoleApi

mr_api = ManagementRoleApi()
await mr_api.api_client.connect_tenant("<tenant_name>")

enabled = await mr_api.management_role_is_mr_enabled()
print(f"MR enabled: {enabled}")
```

## Notes

- ManagementRoleApi is used for node-level operations: repair, quarantine, safety checks.
- **Read-only methods** (safe for automation):
  - `get_mr_role_instance_states()` — current state of all MR-managed role instances
  - `get_quarantine_status()` — quarantined nodes
  - `get_mr_node_repair_history()` — repair history
  - `get_mr_fabric_jobs()` — active fabric jobs
  - `is_mr_enabled()` — whether MR is enabled
  - `get_all_safety_checks()` / `get_applicable_safety_checks()` — safety check results
- **Mutating methods** (gate behind approval):
  - `management_role_request_repair(...)` — request a node repair
  - `management_role_quarantine_role_instances(...)` — quarantine nodes
  - `management_role_un_quarantine_role_instances(...)` — un-quarantine
  - `management_role_clean_up_mr_repair_state(...)` — clean up repair state
