# Step 3 — Restart offending role instances

> **Parent TSG**: [bad-nodes-oos](../bad-nodes-oos.md)
> **Maps to**: `_step_3_restart_role_instances()` method

## Purpose
Restart the identified bad role instances via XDS, creating process dumps for later analysis. After restart, verify whether the problem is resolved to decide if OOS escalation is needed.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `role_instance_names` | `list[str]` | TSG input |
| `node_health_grades` | `dict[str, int]` | From Step 2 — health classification |
| `incident_id` | `int` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `restart_successful` | `bool` | Whether restart resolved the problem |
| `restarted_instances` | `list[str]` | Role instances that were restarted |
| `dump_taken_instances` | `list[str]` | Role instances where process dump was captured (max 2–3) |

## Processing Logic

### 3a. Select role instances to restart
1. From `node_health_grades`, identify instances with health grade ≥ 3 (healthy/degraded) — these are candidates for restart.
2. Instances with health grade ≤ 2 should skip to Step 4 (OOS) unless restart is attempted first.
3. Determine restart scope:
   - **Process-isolated problem** (single bad role process): select only the suspected role instance.
   - **Machine-level issues** (affects multiple roles): select all XFE-related roles on the offending node.

```python
from xds_client import RoleInstancesApi

role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant("<tenant_name>")

all_roles = await role_api.role_instances_get_role_instances()

# Find all XFE-related roles on the same node for machine-level issues
target_node_id = "<node_id>"
node_roles = [r for r in all_roles if r.node_id == target_node_id 
              and r.role_name and "xfe" in r.role_name.lower()]
```

### 3b. Restart via XDS
1. Visit XDS > Tenant Status > Role Summary.
2. Select the target role instance(s).
3. Click **Restart Selected** → **Create Role process dump & restart Role**.
4. If restarting many nodes, only take dumps on 2–3 nodes to avoid excessive overhead.

> **Note**: The XDS restart operation is mutating. In automation, this requires appropriate permissions beyond `StoragePlatformServiceViewer`. The `xds_client` may expose restart methods, but these need approval gates.

### 3c. Verify problem resolution
1. Wait for role instances to come back online (monitor via XDS ping):

```python
from xds_client import RoleInstancesApi, models
import asyncio

role_api = RoleInstancesApi()
await role_api.api_client.connect_tenant("<tenant_name>")

# Wait then ping restarted instances
await asyncio.sleep(120)  # Wait 2 minutes for restart

ping_params = models.PingRequestParams(
    role_instance_names=["<role_instance_name>"],
    request_role_ping=True,
    request_rdma_ping=False,
    request_log_agent_ping=True,
)
ping_results = await role_api.role_instances_ping(ping_params)

for p in ping_results:
    print(f"{p.role_instance_name}: role={p.role_status}, uptime={p.system_up_time}")
```

2. Check that the original problem symptoms (latency, availability) have improved.
3. Take a **historical view (7+ days)** — repeat offenders demand more careful mitigation.

| Verification Result | Next Action |
|---|---|
| Problem resolved, role responsive | Record `mitigation_result = "restarted"`, proceed to Step 5 for follow-up |
| Problem persists or role unresponsive | Proceed to Step 4 — escalate to OOS |
| Repeat offender (7-day history shows recurrence) | Proceed to Step 4 even if currently resolved |

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: 
  - xds-api-call (RoleInstancesApi.role_instances_get_role_instances — list roles on node; RoleInstancesApi.role_instances_ping — verify restart)
  - icm-get-incident (add_description — record restart actions in ICM)
AUTOMATABLE: Partially
  - 3a (Select instances): Yes — role listing and filtering is read-only
  - 3b (Restart): No in automation — XDS restart with dump is mutating; requires SAW or elevated permissions. Automation can generate XDS portal link with pre-selected instances.
  - 3c (Verify): Yes — ping is read-only via xds-api-call
MANUAL_FALLBACK: Use XDS UX to select role instances and click Restart Selected > Create Role process dump & restart Role.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Does `xds_client` expose a restart method (e.g., `role_instances_restart()`)? The coding ability docs mention "restart capabilities" but don't list the specific method signature. |
| 2 | What specific metrics/events should be checked to verify the problem is resolved? The source says "verify the problem is gone" but doesn't specify dashboards or queries. |
| 3 | How long to wait after restart before checking? The 2-minute wait in the code above is an estimate — what's the recommended wait time? |
| 4 | For "repeat offenders," what data source should be queried for 7-day history? Is there an XDS or Kusto table tracking role instance restarts? |
