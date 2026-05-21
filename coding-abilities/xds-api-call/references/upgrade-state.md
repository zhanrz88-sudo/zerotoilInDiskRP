# Upgrade / Deployment State API patterns

These examples show how to query upgrade state, check if a deployment is in progress, and inspect domain readiness.

## Example: Get current upgrade state

```python
from xds_client import UpgradeStateApi

tenant_name = "<tenant_name>"  # e.g. "MS-AM5PrdStr04A"

api = UpgradeStateApi()
await api.api_client.connect_tenant(tenant_name)

state = await api.upgrade_state_get_upgrade_state()

print(f"Upgrade status:  {state.upgrade_status}")
print(f"Domain type:     {state.current_domain_type}")
print(f"Domain ID:       {state.current_domain_id}")
print(f"Task:            {state.current_task_name} ({state.current_task_status})")
print(f"Description:     {state.upgrade_description}")
print(f"Upgrade client:  {state.upgrade_client}")
print(f"Batch:           {state.current_batch_id} / {state.batch_count}")
print(f"Domain sequence: {state.domain_id_sequence}")
print(f"Est. completion: {state.estimated_completion_time}")
```

Inspired by:
- jupyter-templates/Xstore/Stream/XStreamIcmRcaOrchestrator.ipynb

## Example: Check if an upgrade is in progress (boolean)

```python
from xds_client import UpgradeStateApi

api = UpgradeStateApi()
await api.api_client.connect_tenant("<tenant_name>")

is_upgrading = await api.upgrade_state_is_upgrade_in_progress()
print(f"Upgrade in progress: {is_upgrading}")
```

## Example: Get role quorums

```python
from xds_client import UpgradeStateApi

api = UpgradeStateApi()
await api.api_client.connect_tenant("<tenant_name>")

quorums = await api.upgrade_state_get_role_quorums()
print(quorums)
```

## Example: Check if a specific domain is ready

```python
from xds_client import UpgradeStateApi

api = UpgradeStateApi()
await api.api_client.connect_tenant("<tenant_name>")

# Check if UD 3 is ready
is_ready = await api.upgrade_state_is_domain_ready(domain_id=3)
print(f"Domain 3 ready: {is_ready}")
```

## Example: Get stamp version information

```python
from xds_client import UpgradeStateApi

api = UpgradeStateApi()
await api.api_client.connect_tenant("<tenant_name>")

version_info = await api.upgrade_state_get_stamp_version_information()
print(version_info)
```

## Notes

- `upgrade_state_get_upgrade_state()` returns an `UpgradeState` object with 20+ fields describing the complete deployment state.
- `upgrade_status` values include: `"Upgrade In Progress"`, `"No Upgrade"`, and others.
- `current_domain_type` is typically `"UD"` (Upgrade Domain) or `"FD"` (Fault Domain).
- `domain_id_sequence` shows the planned order of domain upgrades.
- For CSM quorum loss TSGs, the critical check is: does `current_domain_id` overlap with an offline CSM's upgrade domain?
- **Mutating methods** (use with caution, gate behind approval):
  - `upgrade_state_book_tenant()` — book the tenant for upgrade
  - `upgrade_state_force_cancel_upgrade()` — force cancel
  - `upgrade_state_prepare_domain_for_roles()` — prepare a domain
  - `upgrade_state_end_upgrade()` — end the upgrade
