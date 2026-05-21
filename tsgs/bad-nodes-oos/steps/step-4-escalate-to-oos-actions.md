# Step 4 — Escalate to out-of-service actions

> **Parent TSG**: [bad-nodes-oos](../bad-nodes-oos.md)
> **Maps to**: `_step_4_escalate_to_oos_actions()` method

## Purpose
If restarting role instances (Step 3) did not resolve the problem, take the node out of service using progressively stronger mechanisms. Tries quarantine first, then OOS marker, then OOS via DC, and finally RDP/FC Shell as last resort.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `role_instance_names` | `list[str]` | TSG input |
| `node_ids` | `list[str]` | TSG input |
| `is_zrs_tenant` | `bool` | TSG input |
| `cloud_environment` | `str` | TSG input |
| `restart_successful` | `bool` | From Step 3 — `False` triggers this step |

## Outputs
| Field | Type | Description |
|---|---|---|
| `oos_method` | `str` | `quarantine` / `oos_marker` / `oos_dc` / `manual_oos` / `failed` |
| `oos_status` | `str` | `InPlaceQuarantine` / `EventualQuarantine` / `applied` / `pending` |
| `actions_taken` | `list[str]` | Audit trail of actions attempted |
| `geneva_action_links` | `list[str]` | Portal links generated for human execution |

## Processing Logic

The step attempts OOS approaches in order. If one approach fails, fall through to the next.

### Option A — Quarantine (short term, ~1 week)

**When to use**: Impact is transient, other roles on the node work well, want to investigate. May bypass prephase throttling.

1. **Execute** Geneva Action `QuarantineRoleInstancesDelegated`:

```python
from xportal import acis

# NOTE: Mutating — requires SAW/dSTS auth
# In automation, generate portal link instead
params = [
    "<tenant_name>",                              # Tenant name (physical for ZRS)
    "<role_instance_1>,<role_instance_2>",         # Comma-separated role instances
]
# ZRS format: "ms-tyo20prdstr01a:xfenativehdfs_in_97"

response = await acis.submit(
    "Xstore",
    "QuarantineRoleInstancesDelegated",
    params,
    endpoint="Production",
)
action_id = response["id"]
```

2. **Check status** via `GetQuarantineStatusDelegated` or read-only XDS API:

```python
from xds_client import ManagementRoleApi

mr_api = ManagementRoleApi()
await mr_api.api_client.connect_tenant("<tenant_name>")
quarantine_status = await mr_api.management_role_get_quarantine_status()
print(quarantine_status)
```

3. **Expected results**:
   - `InPlaceQuarantine`: immediate, 5–10 minutes
   - `EventualQuarantine`: queued, can take hours

4. If quarantine succeeds → proceed to Step 5.
5. If quarantine fails → try Option B.

**Reversal**: `UnQuarantineRoleInstancesDelegated`

### Option B — Set OOS Role Marker (medium term, persists until next STG upgrade)

1. **Execute** Geneva Action `SetRoleInstanceOOSExternalWithSafetyChecksDelegated`:

```python
# Mutating — requires SAW/dSTS auth
params = [
    "Production",         # Endpoint
    "<tenant_name>",      # Fully qualified tenant (physical for ZRS)
    "<node_id>",          # From XDS > Tenant Status > Roles Summary
    "<role_instance_id>", # Role instance name
]

response = await acis.submit(
    "Xstore",
    "SetRoleInstanceOOSExternalWithSafetyChecksDelegated",
    params,
    endpoint="Production",
)
```

2. **XDS fallback** (if GA fails): Use XDS > Restart Role & mark it out-of-service (OOS).
3. If successful → proceed to Step 5.
4. If both GA and XDS fail → try Option C.

**Reversal**: `SetRoleInstanceInServiceWithSafetyChecksDelegated` or XDS > Restart Role and mark in-service.

### Option C — Set OOS via DC (long term, permanent until manually reverted)

**Requires additional JIT**: `Storage-DynamicConfigUpdateRole`.

Role instances parse the SLB OOS DC on start. If their node number is in the list, they ping down to SLB.

1. **Preferred**: Execute Geneva Action `TakeFERoleInstanceOOSViaDC`:

```python
# Mutating — requires SAW/dSTS auth + DynamicConfigUpdateRole JIT
response = await acis.submit(
    "Xstore",
    "TakeFERoleInstanceOOSViaDC",
    ["<tenant_name>", "<instance_number>"],
    endpoint="Production",
)
```

   - May fail when another DC update is being rolled out — **retry**.

2. **XDS fallback** (if GA fails): Update DC via XDS directly:
   1. XDS > XML Dynamic Config > Configuration > Refresh
   2. Add numeric instance ID to the appropriate setting:
      - Native XFE: `XStoreConfigSettings/NativeXfe/Common/BackgroundSettings/SlbOutOfRotationInstanceIds`
      - Managed XFE (Blob/Table/Queue): see `_references.md` for paths
   3. If config rollout is in progress, edit **BOTH** XML files
   4. Note down `VersionIdentifier` and click Validate & Save
   5. Verify change took effect

3. If successful → proceed to Step 5.
4. If both GA and XDS fail → try Option D.

### Option D — Last resort: RDP / FC Shell (fully manual)

**CRITICAL**: MUST work with a second DRI with screen share. FC Shell can impact the entire node.

1. Request JIT: RDP (using Cluster, Tenant, Role), LocalAdministrator
2. Connect to node via RDP
3. Find drive with the role's `.exe` file
4. Rename `.exe` to `.exe.disabled`
5. Kill process from Task Manager
6. If process still alive, use FC Shell
7. Proceed to Step 5

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY:
  - geneva-action-call (QuarantineRoleInstancesDelegated, GetQuarantineStatusDelegated, SetRoleInstanceOOSExternalWithSafetyChecksDelegated, TakeFERoleInstanceOOSViaDC — all mutating, require SAW/dSTS)
  - xds-api-call (ManagementRoleApi.management_role_get_quarantine_status — read-only status check; DynamicConfigApi — read config for OOS via DC)
AUTOMATABLE: Partially
  - Option A (Quarantine): Automation can prepare params + generate portal link; status check is automatable via xds-api-call
  - Option B (OOS Marker): Automation can prepare params + generate portal link; XDS fallback also requires elevated permissions
  - Option C (OOS via DC): Automation can prepare params + generate portal link; XDS DC edit requires DynamicConfigUpdateRole
  - Option D (RDP/FC Shell): Fully manual — no automation path
MANUAL_FALLBACK: Execute all Geneva Actions via portal.microsoftgeneva.com on SAW. Use XDS UX for fallback operations. For Option D, RDP to node with second DRI.
```

## Open Questions
| # | Question |
|---|---|
| 1 | What are the exact positional parameter lists for `QuarantineRoleInstancesDelegated`? The source describes tenant name and role instances but doesn't give the `acis.execute()` parameter order. |
| 2 | What are the exact positional parameters for `SetRoleInstanceOOSExternalWithSafetyChecksDelegated`? Source lists Endpoint, Tenant Name, Node Id, Role Instance ID — is that the correct `params` list order? |
| 3 | What are the exact parameters for `TakeFERoleInstanceOOSViaDC`? Is it tenant name + instance number, or are there additional parameters? |
| 4 | How long to wait after quarantine/OOS before verifying the action took effect? Source says InPlaceQuarantine is 5–10 min, EventualQuarantine can take hours. |
| 5 | For ZRS tenants, what is the format for role instance names in GA parameters? Source shows `ms-tyo20prdstr01a:xfenativehdfs_in_97` — is this `<physical_tenant>:<role_instance>`? |
| 6 | When editing DC XML via XDS fallback (Option C), how do you identify which of the two XML files to edit when a config rollout is in progress? |
| 7 | For Option D (RDP), how do you identify which drive contains the role's `.exe`? Is there a standard path convention? |
