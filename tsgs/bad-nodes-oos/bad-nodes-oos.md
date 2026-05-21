# Taking Bad Role Instances Out of Service

> **Source**: [Taking bad role instances out of service](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=Frontend_Layer/tsgs/miscellaneous/bad-nodes-oos.md&version=GBmaster)

## Purpose

Mitigates incidents caused by a single (or small set of) bad frontend role instances that are behind latency and/or availability problems. The TSG follows an escalating approach: preserve diagnostics → restart → quarantine → OOS marker → OOS via DC → last resort RDP/FC Shell, then request MR repair and file follow-up bugs. Applies to all clouds.

**Critical principle**: Diagnosing the root cause as a "bad node" and restarting is insufficient. The root cause behind the misbehavior must be understood to fix bugs or ensure self-healing mechanisms prevent future impact.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `int` | ICM incident being worked |
| `tenant_name` | `str` | Physical tenant name hosting the bad role instance(s) |
| `role_instance_names` | `list[str]` | Names of suspected bad role instances (e.g., `["Nephos.Queue_IN_94", "xfenativehdfs_in_97"]`) |
| `cloud_environment` | `str` | `Production` / `Mooncake` / `Fairfax` / `USNat` / `USSec` |
| `node_ids` | `list[str]` | Node IDs (from XDS Role Summary) for the affected role instances |
| `is_zrs_tenant` | `bool` | Whether the tenant is ZRS (affects parameter formatting) |

## Outputs

| Field | Type | Description |
|---|---|---|
| `mitigation_result` | `str` | `restarted` / `quarantined` / `oos_marker` / `oos_dc` / `manual_oos` / `escalated` |
| `actions_taken` | `list[str]` | Sequence of actions attempted (for audit trail) |
| `diagnostic_links` | `list[str]` | Log Collector links, DGrep links, trace links saved to ICM |
| `follow_up_bug_id` | `str` | Bug ID filed for root cause investigation |

## Steps

### Step 1 — Request JIT access

[Step Analysis](steps/step-1-request-jit-access.md)

Request JIT access for the offending physical tenant:

| Resource Type | Instance | Access Level |
|---|---|---|
| XDS | `<tenant_name>` | Storage-PlatformServiceOperator |

For OOS via DC (Step 4, long-term option), also request:

| Resource Type | Instance | Access Level |
|---|---|---|
| XDS | `<tenant_name>` | Storage-DynamicConfigUpdateRole |

For non-public clouds, use the right JIT portal per [aka.ms/jit](https://aka.ms/jit).

### Step 2 — Collect diagnostic logs and check node health

[Step Analysis](steps/step-2-collect-diagnostics-and-check-health.md)

Before restarting, preserve debugging information:

1. **Collect logs** — Use Log Collector diagnostics tool in XPortal. Save generated links into the ICM.
2. **Check node health** — Query DGrep for `ServerStatsEx1` events in the Xstore namespace:
   - Scope: `TableServer contains xtableserver_in_<N>` (where N = instance number on the node)
   - Health grade: 4 (Healthy) → 1 (Unhealthy)
   - Nodes reporting healthy → restart first and monitor
   - Nodes reporting unhealthy → take FE roles OOS directly
3. **Take CPU trace** (if restarting many nodes, only 2–3 traces needed):
   - Use `Start-XdsCpuProfile` from XDiagCmdLet against the tenant
   - Or use `RunXDiagCmdLetScript` Geneva Action

### Step 3 — Restart offending role instances

[Step Analysis](steps/step-3-restart-role-instances.md)

1. Visit XDS > Tenant Status > Role Summary for the affected tenant.
2. Select the bad role instance(s):
   - **Process-isolated problem**: select single role instance.
   - **Machine-level issues**: select all XFE-related roles on the offending node.
3. Click **Restart Selected** → **Create Role process dump & restart Role**.
   - If restarting many nodes, only take dumps on 2–3 nodes.
4. Verify the problem is gone after restarts.

| Decision | Action |
|---|---|
| Problem resolved | Record `mitigation_result = "restarted"`, proceed to Step 5 for follow-up |
| Problem persists | Proceed to Step 4 — escalate to OOS |

> **Historical check**: When checking metrics, take a 7+ day view. Repeat offenders demand more careful mitigation.

### Step 4 — Escalate to out-of-service actions

[Step Analysis](steps/step-4-escalate-to-oos-actions.md)

**Only take this action if restart (Step 3) was ineffective.** Safety first, then tenant health.

Try in order of increasing severity:

#### Option A — Quarantine (short term, ~1 week)

Gracefully removes the node from rotation. Use when impact is transient and other roles on the node work well.

1. Execute Geneva Action: `QuarantineRoleInstancesDelegated` from SAW with AME account.
   - Tenant name (for ZRS: physical tenant)
   - Role instances as comma-separated list (e.g., `Nephos.Queue_IN_94,Nephos.File_IN_12`)
   - For ZRS: `ms-tyo20prdstr01a:xfenativehdfs_in_97`
2. Check status: `GetQuarantineStatusDelegated`
3. Results: `InPlaceQuarantine` (immediate, 5–10 min) or `EventualQuarantine` (queued, can take hours)
4. Proceed to Step 5 (request MR + follow-up)

Reversal: `UnQuarantineRoleInstancesDelegated`

#### Option B — Set OOS Role Marker (medium term, until next STG upgrade)

Sets OOS marker on the role instance's VHD. Persists until STG upgrade.

1. Execute Geneva Action: `SetRoleInstanceOOSExternalWithSafetyChecksDelegated`
   - Endpoint: `Production`
   - Tenant Name: fully qualified (for ZRS: physical tenant)
   - Node Id: from XDS > Tenant Status > Roles Summary
   - Role Instance ID: name of the role instance
2. **XDS fallback**: If GA fails, use XDS > Restart Role & mark it out-of-service (OOS)
3. Proceed to Step 5 (request MR + follow-up)

Reversal: `SetRoleInstanceInServiceWithSafetyChecksDelegated` or XDS > Restart Role and mark in-service

#### Option C — Set OOS via DC (long term, permanent until reverted)

Role instances parse the SLB OOS DC on start; if their node number is listed, they ping down to SLB.

Requires additional JIT: `Storage-DynamicConfigUpdateRole`.

1. **Preferred**: Execute Geneva Action `TakeFERoleInstanceOOSViaDC` under XStore > XFE Operations
   - May fail if another DC update is rolling out — retry
2. **XDS fallback**: If GA fails, update DC via XDS directly:
   - XDS > XML Dynamic Config > Configuration > Refresh
   - Add numeric instance ID to the appropriate OOS setting (see `_references.md` for paths)
   - If config rollout is in progress, edit BOTH XML files
   - Note down `VersionIdentifier`, click Validate & Save
   - Verify change took effect
3. Proceed to Step 5 (request MR + follow-up)

#### Option D — Last resort: RDP / FC Shell (fully manual)

**MUST work with a second DRI with screen share.** FC Shell can impact the entire node.

1. Request JIT: RDP (using Cluster, Tenant, Role), LocalAdministrator
2. Connect to node via RDP
3. Find drive with the role's `.exe`
4. Rename `.exe` to `.exe.disabled`
5. Kill process from Task Manager
6. If process still alive, use FC Shell
7. Proceed to Step 5 (request MR + follow-up)

### Step 5 — Request MR repair and create follow-up tasks

[Step Analysis](steps/step-5-request-mr-repair-and-follow-up.md)

#### Request MR Repair (if hardware suspected)

1. **Preferred**: Execute Geneva Action `RequestRepairActionFromMRDelegated`:
   - Tenant Name: for ZRS use virtual ZRS tenant
   - Role Instance ID: use one role instance (for ZRS include physical tenant prefix)
   - Requested Repair Action: `RMA`
   - Repair Reason: describe the issues
   - Repair Fault Code: `0`
2. **XDS fallback**: XDS > Role Summary > Request MR Repair
   - Fault Reason: describe issues
   - Repair Type: `RMA`
   - Fault Code: `0`

#### Create Follow-up Tasks

1. Download role instance log files from XDS via Log File Explorer
2. Download `.etl` files for traces from XDS via Log File Explorer
3. Search for crash dump in Azure Watson
4. File a bug under `One\XStore\XFE` with links to:
   - Log files
   - Trace .etl files
   - Watson crash dump (if found)
   - ICM incident

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: 
  - geneva-action-call (QuarantineRoleInstancesDelegated, GetQuarantineStatusDelegated, SetRoleInstanceOOSExternalWithSafetyChecksDelegated, TakeFERoleInstanceOOSViaDC, RequestRepairActionFromMRDelegated — all mutating, require SAW/dSTS)
  - xds-api-call (RoleInstancesApi.role_instances_get_role_instances, RoleInstancesApi.role_instances_ping, ManagementRoleApi.management_role_get_quarantine_status, DynamicConfigApi — read-only diagnostics)
  - dgrep-query (Xstore/ServerStatsEx1 — node health check)
  - icm-get-incident (add_description — save diagnostic links to ICM)
  - xds-log-search (search_log, generate_log_search_link — log collection)
TSG_CALL: None (single source document, no external TSG calls)
AUTOMATABLE: Partially (Steps 1-2 diagnostics are automatable; Steps 3-5 mutating actions require SAW/human approval — automation can prepare params and generate portal links)
MANUAL_FALLBACK: Execute all Geneva Actions via portal.microsoftgeneva.com on SAW; use XDS UX for restarts, OOS, and MR repair requests.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can the Log Collector diagnostics tool in XPortal be invoked programmatically, or is it a manual UI-only tool? |
| 2 | What specific metrics/events should be checked in Step 3 to verify the problem is resolved after restart? (Source says "verify" but doesn't specify which metrics.) |
| 3 | How should ZRS tenants be handled differently in automation? The source mentions "physical tenant" vs "virtual ZRS tenant" in different steps — need a mapping function. |
| 4 | What are the exact positional parameter lists and ordering for each Geneva Action operation ID? (The `acis.execute()` pattern takes `params: List[str]` — parameter order matters but is not validated in any existing notebook.) |
| 5 | How long should automation wait after quarantine/OOS before verifying the action took effect? Source says InPlaceQuarantine is 5–10 min and EventualQuarantine can take hours. |
| 6 | What is the correct approach for "repeat offenders" mentioned in the source? Should automation check 7-day history automatically and flag repeat bad nodes? |
| 7 | ~~Is there a programmatic API to check quarantine status?~~ **Resolved**: Yes — `ManagementRoleApi.management_role_get_quarantine_status()` (read-only, via `xds-api-call` coding ability) and `GetQuarantineStatusDelegated` Geneva Action. |
| 8 | The source mentions `Start-XdsCpuProfile` from XDiagCmdLet — is this accessible via the `RunXDiagCmdLetScript` Geneva Action, or only via PowerShell on SAW? |
