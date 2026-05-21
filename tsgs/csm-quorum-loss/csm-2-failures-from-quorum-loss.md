# CSM 2 Failures Away from Quorum Loss

> **Source**: [CSM Quorum Loss TSG (ADO)](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/CSM%20Quorum%20Loss%20TSG.md&_a=preview)
> **Incident Example**: [ICM 498642417](https://portal.microsofticm.com/imp/v3/incidents/details/498642417/home)

## Scenario

This alert triggers when a storage tenant is **2 CSMs away from quorum loss** (typically 3+ CSMs offline). Common causes:

| Cause | Description |
|---|---|
| Hardware fault (HI) | CSM nodes in HumanInvestigate |
| Hardware fault (OFR) | CSM nodes in OutForRepair |
| Deployment overlap | Active xDep deployment taking an additional CSM offline |
| Combination | 2+ CSMs already down + deployment taking 1 more |

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | ICM alert title (e.g., `MS-DUB07PrdStr12B`) |
| `cloud_environment` | `str` | `Public` / `USSec` / `USNat` |

## Outputs

| Field | Type | Description |
|---|---|---|
| `offline_csms` | `list[dict]` | CSM instances found offline |
| `deployment_active` | `bool` | Whether a deployment is contributing |
| `node_states` | `list[dict]` | Per-node fabric state and fault info |
| `recovery_results` | `list[dict]` | Per-node recovery outcome |
| `escalation_needed` | `bool` | Whether manual escalation was required |

## Steps

### Step 1 — Identify offline CSMs

[Step Analysis](steps/step-1-identify-offline-csms.md)

Connect to XDS for the tenant via `ApiClient.connect_tenant(tenant_name)`. List all CSM role instances via `RoleInstancesApi.role_instances_get_role_instances()`. Ping all instances via `RoleInstancesApi.role_instances_ping(PingRequestParams)`.

Record for each CSM: role instance name (e.g., `csm_in_5`), Node ID (GUID), Update Domain (UD), Fault Domain (FD), ping result (Responsive/Unresponsive).

Filter to instances where ping result = Unresponsive → `offline_csms`.

### Step 2 — Check deployment status

[Step Analysis](steps/step-2-check-deployment-status.md)

Query `UpgradeStateApi.upgrade_state_get_upgrade_state()` for the tenant. Record: `is_active`, `current_ud`, `version`.

Check UD overlap between `deployment_ud` and offline CSM UDs.

| Condition | Action |
|---|---|
| `deployment_active` AND `icm_severity == Sev2` (1 away) | Contact `xdep@microsoft.com` → **block upgrade immediately** |
| `deployment_active` AND `icm_severity == Sev3` (2 away) | Continue node repairs; avoid repairing nodes in active UD/FD |
| `deployment_active == false` | No action needed |

### Step 3 — Identify node state for each offline CSM

[Step Analysis](steps/step-3-identify-node-state.md)

For each offline CSM node, query Kusto for fabric state:

```kusto
GetAllStorageNodeFabricHealth
| where NodeId contains "<node_id>"
| project ClusterId, Tenant, NodeId, TMState, DCMState,
          HIFault, HIFaultReason, HIFaultTime,
          OFRFaultCode, OFRFaultReason
```

Map `TMState` → `node_state` (HI / OFR / Ready / Other). If Kusto shows Ready but XDS ping was Unresponsive, warn about stale data and recommend FcShell manual verification.

### Step 4 — Recover nodes by state

[Step Analysis](steps/step-4-recover-nodes.md)

For each node, branch by `node_state`:

| State | Action |
|---|---|
| **HI** | **HI recovery sequence**: (1) Check fault-code-specific TSG — **Calls**: [storage-node-recovery](../storage-node-recovery/storage-node-recovery.md) (FC 8, 70007, 43030). (2) Reset Node Health via Geneva Action `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`. (3) If still HI, Power Cycle via `PowerNodeWithSafetyChecksDelegated` then Reset again. (4) If still HI, escalate to XSSE DRI (Public) or `xsse-tented@` (AGC). |
| **OFR** | **OFR handling**: Public → **Calls**: [escalate-gdco-tickets](../escalate-gdco-tickets/escalate-gdco-tickets.md) with severity. AGC → annotate ICM, escalate to `xsse-tented@`. |
| **Ready** (roles not starting) | Wait ~45 min, then escalate to XSSE FTE |
| **Other** | Wait for node to fault or recover |

**HI Recovery Prerequisites:** JIT `FFE/PlatformAdministrator`. Work one node per tenant at a time. Check for active DU first.

**Allowed Geneva Actions (non-XSSE DRIs):** `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`, `PowerNodeWithSafetyChecksDelegated`, `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated`. Others require XSSE FTE approval.

**CSM Software Issues**: If CSM role crashing (not hardware), check logs for asserts/exceptions, use CSM Quorum Health dashboard, contact `xcsmdev@microsoft.com`.

### Step 5 — Post-mitigation

[Step Analysis](steps/step-5-post-mitigation.md)

- The monitor self-mitigates after **120 minutes** of healthy status.
- Even if ICM self-mitigates, **continue driving recovery** of remaining offline CSMs.
- **Public**: XSSE DRI + Ops own follow-up.
- **AGC**: XSSE team members must be alerted.

## Severity Guide

| Situation | ICM Severity | GDCO Action |
|---|---|---|
| 2 away from quorum | Sev3 **Expedite** | Expedite GDCO tickets |
| 1 away from quorum | Sev2 | Link GDCO to Sev2; start bridge |
| Quorum loss (DU) | Sev2 | Follow [DU TSG](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Data%20Unavailability%20Alert%20%28DU%29.md&_a=preview) |

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: xds-api-call (RoleInstancesApi.role_instances_ping, UpgradeStateApi.upgrade_state_get_upgrade_state, ManagementRoleApi), kusto-query (GetAllStorageNodeFabricHealth), geneva-action-call (ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PowerNodeWithSafetyChecksDelegated), icm-get-incident (Incident.add_description)
TSG_CALL: escalate-gdco-tickets (for OFR nodes), storage-node-recovery (for HI nodes with known fault codes)
AUTOMATABLE: Partially (Steps 1-3 fully automatable; Step 4 HI recovery requires human approval for Geneva Actions; OFR requires GDCO management; Step 5 monitoring requires human follow-up)
MANUAL_FALLBACK: Use XDS Portal UI for role pings, FcShell for node state, Geneva Actions portal for recovery, GDCO App for ticket management.
```

## Open Questions

| # | Question | Impact |
|---|---|---|
| 1 | Exact CSM quorum threshold per tenant (is it always `total_csms - 2`?) | Needed to compute severity automatically |
| 2 | Self-mitigation monitor metric path in Geneva | Needed to detect re-alert risk |
| 3 | When does CSM quorum loss escalate to DU TSG vs. stay in this TSG? | Orchestration boundary |
| 4 | How stale is Kusto data typically? (minutes? hours?) | Affects reliability of Step 3 |
| 5 | Complete fault code → recovery mapping (only FC 8, 70007, 43030 are documented) | Step 4 decision completeness |
| 6 | How to check if a GDCO ticket already exists for a node programmatically? | OFR handling in Step 4 |
