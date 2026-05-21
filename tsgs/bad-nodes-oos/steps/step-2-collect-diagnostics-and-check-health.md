# Step 2 — Collect diagnostic logs and check node health

> **Parent TSG**: [bad-nodes-oos](../bad-nodes-oos.md)
> **Maps to**: `_step_2_collect_diagnostics_and_check_health()` method

## Purpose
Preserve debugging information before any restart or OOS action. Collects logs, checks node health via DGrep, and optionally takes a CPU trace. This data is critical for root cause analysis — restarting blindly destroys diagnostic state.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `role_instance_names` | `list[str]` | TSG input |
| `incident_id` | `int` | TSG input |
| `cloud_environment` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `log_collector_links` | `list[str]` | URLs from Log Collector diagnostics tool |
| `node_health_grades` | `dict[str, int]` | Map of role instance → health grade (1–4) |
| `unhealthy_instances` | `list[str]` | Role instances with health grade ≤ 2 (candidates for immediate OOS) |
| `healthy_instances` | `list[str]` | Role instances with health grade ≥ 3 (candidates for restart first) |
| `cpu_trace_links` | `list[str]` | Links to CPU trace results (if taken) |
| `dgrep_link` | `str` | Shareable DGrep query link |

## Processing Logic

### 2a. Collect logs via Log Collector
1. Open Log Collector diagnostics tool in XPortal for the affected role instances.
2. Save generated download links.
3. Post links to the ICM incident:

```python
from xportal import icm

incident = await icm.get_incident(<incident_id>)
links_text = "Log Collector links for bad node investigation:\n" + "\n".join(log_collector_links)
await incident.add_description(links_text)
```

### 2b. Check node health via DGrep
Query `ServerStatsEx1` events to get health grades reported by Table Server:

```python
import datetime
from xportal import dgrep
from xstore.common.dgrep import get_moniker_by_xstore_tenant
from zerotoil.core.framework import dgrep_query_with_retry

tenant_name = "<tenant_name>"
moniker = await get_moniker_by_xstore_tenant(tenant_name)

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=10)

# Query ServerStatsEx1 for node health — use contains matching for TableServer field
server_query = 'where TableServer.Contains("<xtableserver_instance>") select TableServer, HealthGrade, PreciseTimeStamp'

result = await dgrep_query_with_retry(
    dgrep,
    namespaces="Xstore",
    event_names="ServerStatsEx1",
    from_time=start_time,
    to_time=end_time,
    server_query=server_query,
    scope_conditions={"Moniker": moniker},
)

df = result.to_df()
dgrep_link = result.get_dgrep_link()

# Classify by health grade
# Grade 4 = Healthy, 3 = Degraded, 2 = Warning, 1 = Unhealthy
```

Decision logic based on health grades:

| Health Grade | Classification | Recommended Next Step |
|---|---|---|
| 4 (Healthy) | `healthy_instances` | Restart first (Step 3), monitor for recovery |
| 3 (Degraded) | `healthy_instances` | Restart first, monitor closely |
| 2 (Warning) | `unhealthy_instances` | Consider OOS if restart fails |
| 1 (Unhealthy) | `unhealthy_instances` | Take FE roles OOS directly (skip to Step 4) |

### 2c. Take CPU trace (optional, for 2–3 nodes when restarting many)
1. Use `Start-XdsCpuProfile` from XDiagCmdLet against the tenant.
2. Or invoke via `RunXDiagCmdLetScript` Geneva Action:

```python
from xportal import acis

# NOTE: This is a mutating action — requires SAW/dSTS auth
# In automation, generate the portal link instead
result = await acis.execute(
    "Xstore",
    "RunXDiagCmdLetScript",
    ["<tenant_name>", "Start-XdsCpuProfile -RoleInstanceName <role_instance_name>"],
)
```

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: 
  - dgrep-query (Xstore/ServerStatsEx1 — node health grades)
  - icm-get-incident (add_description — post log links to ICM)
  - geneva-action-call (RunXDiagCmdLetScript — CPU trace, mutating)
AUTOMATABLE: Partially
  - 2a (Log Collector): Manual — no known programmatic API for Log Collector tool
  - 2b (DGrep health check): Yes — fully automatable via dgrep-query coding ability
  - 2c (CPU trace): Partially — RunXDiagCmdLetScript GA requires SAW auth; automation can generate portal link
MANUAL_FALLBACK: Use Log Collector in XPortal UI; query DGrep manually; run Start-XdsCpuProfile from PowerShell on SAW.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can the Log Collector diagnostics tool be invoked programmatically? No API documented in coding abilities. |
| 2 | What is the exact field name for health grade in `ServerStatsEx1`? The source says "Health grade" — is the DGrep field named `HealthGrade`, `Health`, or something else? |
| 3 | Does `ServerStatsEx1` have a field to filter by node/role instance directly, or only via `TableServer contains` matching? |
| 4 | Is `RunXDiagCmdLetScript` the correct GA operation ID for `Start-XdsCpuProfile`, or is there a dedicated CPU profiling GA? |
| 5 | For ZRS tenants, does the DGrep moniker resolution work with physical or virtual tenant name? |
