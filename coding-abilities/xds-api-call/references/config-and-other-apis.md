# Dynamic Config / Account Settings / Other APIs

These examples cover the less frequently used but still important XDS API families.

## Example: Read dynamic config settings

```python
from xds_client.api.dynamic_config_api import DynamicConfigApi
from xds_client import ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
config_api = DynamicConfigApi(client)

# Read config settings for the tenant
# result = await config_api.dynamic_config_get_configuration_settings(...)
```

Inspired by:
- jupyter-templates/Xstore/XInvestigator/mooncakeTest.ipynb

## Example: Account settings query

```python
from xds_client.api.account_settings_api import AccountSettingsApi
from xds_client import ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
acct_api = AccountSettingsApi(client)

# Query account-level settings
# result = await acct_api.account_settings_<method_name>(...)
```

Inspired by:
- jupyter-templates/Xstore/XInvestigator/mooncakeTest.ipynb

## Example: LB rules query

```python
from xds_client.api.lb_rules_api import LbRulesApi
from xds_client import ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
lb_api = LbRulesApi(client)

# Query load balancing rules
# result = await lb_api.lb_rules_<method_name>(...)
```

Inspired by:
- jupyter-templates/Xstore/XInvestigator/mooncakeTest.ipynb

## Example: GeoRepair via XTableGeoApi

```python
from xds_client import XTableGeoApi, GeoRepairActionArgs, RowKeyArgs, ApiClient

client = ApiClient()
await client.connect_tenant("<tenant_name>")
geo_api = XTableGeoApi(client)

# NOTE: Geo repair is a MUTATING operation — gate behind confirmation
# args = GeoRepairActionArgs(...)
# result = await geo_api.x_table_geo_<method_name>(args)
```

Inspired by:
- jupyter-templates/Xstore/XTable/GC/Rebootstrap.ipynb

## Complete list of API classes available in xds_client

| Class | Module path |
|---|---|
| `AccountApi` | `xds_client.api.account_api` |
| `AccountSettingsApi` | `xds_client.api.account_settings_api` |
| `AuthenticationMetadataApi` | `xds_client.api.authentication_metadata_api` |
| `ClusterSharingConfigApi` | `xds_client.api.cluster_sharing_config_api` |
| `ConfigRolloutApi` | `xds_client.api.config_rollout_api` |
| `DynamicConfigApi` | `xds_client.api.dynamic_config_api` |
| `FaultInjectionCommandApi` | `xds_client.api.fault_injection_command_api` |
| `LbRulesApi` | `xds_client.api.lb_rules_api` |
| `ManagementRoleApi` | `xds_client.api.management_role_api` |
| `ParallaxConfigApi` | `xds_client.api.parallax_config_api` |
| `RoleInstancesApi` | `xds_client.api.role_instances_api` |
| `SmokeTestApi` | `xds_client.api.smoke_test_api` |
| `TenantApi` | `xds_client.api.tenant_api` |
| `UpgradeStateApi` | `xds_client.api.upgrade_state_api` |
| `XAggregatorApi` | `xds_client.api.x_aggregator_api` |
| `XCacheApi` | `xds_client.api.x_cache_api` |
| `XComputeApi` | `xds_client.api.x_compute_api` |
| `XLockApi` | `xds_client.api.x_lock_api` |
| `XMeterApi` | `xds_client.api.x_meter_api` |
| `XNamespaceApi` | `xds_client.api.x_namespace_api` |
| `XStreamApi` | `xds_client.api.x_stream_api` |
| `XStreamCommandsApi` | `xds_client.api.x_stream_commands_api` |
| `XTableApi` | `xds_client.api.x_table_api` |
| `XTableGeoApi` | `xds_client.api.x_table_geo_api` |
| `XTableServersApi` | `xds_client.api.x_table_servers_api` |
| `XvNextApi` | `xds_client.api.xv_next_api` |
| `XdsWebApi` | `xds_client.api.xds_web_api` |

## Notes

- All API classes follow the same pattern: instantiate with optional `ApiClient`, connect to tenant, call methods.
- The `xds_client` package is auto-generated from the XDS REST API Swagger spec.
- Model objects are in `xds_client.models` — import specific models as needed (e.g., `PingRequestParams`, `ReadTableArgs`, `RowKeyArgs`).
