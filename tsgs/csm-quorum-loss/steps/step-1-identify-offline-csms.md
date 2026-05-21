# Step 1 — Identify offline CSMs

> **Parent TSG**: [csm-2-failures-from-quorum-loss](../csm-2-failures-from-quorum-loss.md)
> **Maps to**: `_step_1_identify_offline_csms()` method

## Purpose

Determine which CSM role instances are offline by pinging them through XDS.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `csm_instances` | `list[dict]` | All CSM instances with: `role_instance`, `node_id`, `update_domain`, `fault_domain`, `status` (online/offline) |
| `offline_csms` | `list[dict]` | Subset where status = offline |
| `offline_count` | `int` | Number of offline CSMs |

## Processing Logic

1. **Connect to XDS for tenant** — Use `ApiClient.connect_tenant(tenant_name)` to connect.

2. **List CSM role instances** — Use `RoleInstancesApi.role_instances_get_role_instances()` to get all CSM instances. Record: role instance name (e.g., `csm_in_5`), Node ID (GUID), Update Domain (UD), Fault Domain (FD).

3. **Ping all CSM instances** — Use `RoleInstancesApi.role_instances_ping(PingRequestParams)`. Returns `list[PingResponse]` with `role_status` per instance.

4. **Filter to offline CSMs** — Instances where ping result = `Unresponsive`.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: xds-api-call (RoleInstancesApi.role_instances_get_role_instances, RoleInstancesApi.role_instances_ping)
AUTOMATABLE: Yes
MANUAL_FALLBACK: Use XDS Portal UI to ping role instances manually.
```

## Open Questions

| # | Question |
|---|---|
| 1 | ~~Is there a programmatic XDS API to ping CSM role instances?~~ **Resolved**: Yes — `RoleInstancesApi.role_instances_ping(PingRequestParams)` returns `list[PingResponse]` with `role_status` per instance. |
| 2 | Can we infer CSM role status from Kusto instead of XDS pings? (May be useful as a secondary check) |
| 3 | ~~What is the XDS URL pattern?~~ **Resolved**: `ApiClient.connect_tenant(tenant_name)` handles routing internally. |
