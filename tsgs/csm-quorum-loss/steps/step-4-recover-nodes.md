# Step 4 — Recover nodes by state

> **Parent TSG**: [csm-2-failures-from-quorum-loss](../csm-2-failures-from-quorum-loss.md)
> **Maps to**: `_step_4_recover_nodes()` method

## Purpose

For each offline CSM node, apply the appropriate recovery action based on its fabric state.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `node_states` | `list[dict]` | From Step 3 |
| `tenant_name` | `str` | TSG input |
| `icm_incident_id` | `str` | TSG input |
| `icm_severity` | `str` | TSG input |
| `cloud_environment` | `str` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `recovery_results` | `list[dict]` | Per-node: `node_id`, `recovery_result` (recovered/still_hi/escalated/gdco_escalated), `actions_taken` |
| `escalation_needed` | `bool` | Whether manual escalation was required for any node |

## Processing Logic

**Branch by node_state:**

| State | Action |
|---|---|
| **HumanInvestigate (HI)** | HI recovery sequence (see below) |
| **OutForRepair (OFR)** | OFR handling (see below) |
| **Ready** (roles not starting) | Wait ~45 min, then escalate to XSSE FTE |
| **Other** | Wait for node to fault or recover |

### HI Recovery Sequence

**Prerequisites:** JIT `FFE/PlatformAdministrator` for cluster. Work one node per tenant at a time. Check for active DU first.

1. **Check known fault-code-specific TSG** — If `fault_code` matches FC 8 / FC 70007 / FC 43030, **Calls**: [storage-node-recovery](../../storage-node-recovery/storage-node-recovery.md). For unknown fault codes, proceed with generic recovery.

2. **Reset Node Health (first attempt)** — Geneva Action: `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`. Parameters: Tenant, NodeId, SkipSafetyChecks=false, IncidentId, IncidentCategory=Node-Recovery. Wait and check if node transitions to Ready.

3. **Power Cycle + Reset Health (second attempt)** — If node falls back to HI, execute `PowerNodeWithSafetyChecksDelegated` (Reboot and Power Cycle on fail), then repeat Reset Health.

4. **Escalate if still HI** — Public: escalate to XSSE DRI on-call. AGC: escalate to `xsse-tented@microsoft.com`.

**Allowed Geneva Actions (non-XSSE DRIs):** `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`, `PowerNodeWithSafetyChecksDelegated`, `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated`. Any other actions require explicit XSSE FTE approval.

### OFR Handling

1. **Branch by environment:**
   - **Public:** Check if GDCO ticket exists. If OFR fault code not in 60k series, determine appropriate 60k code. **Calls**: [escalate-gdco-tickets](../../escalate-gdco-tickets/escalate-gdco-tickets.md) with severity based on ICM severity.
   - **AGC:** Annotate NodeId + Fault Code in ICM, escalate to `xsse-tented@microsoft.com`.

2. **Hardware parts availability:** If GDCO created but parts unavailable, XSSE FTE on-call looks for in-cluster salvage (decom/OFR nodes), regardless of SKU generation. Do not take parts from racks with CSMs.

### CSM Software Issues

If CSM role itself is crashing (not hardware): check logs for asserts/exceptions, use CSM Quorum Health dashboard, contact `xcsmdev@microsoft.com`.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PowerNodeWithSafetyChecksDelegated), xds-api-call (ManagementRoleApi for quarantine/repair status), icm-get-incident (Incident.add_description)
TSG_CALL: escalate-gdco-tickets (for OFR nodes), storage-node-recovery (for HI nodes with known fault codes)
AUTOMATABLE: Partially (quarantine check = read-only; Geneva Actions require SAW/dSTS auth or human approval; OFR handling requires GDCO ticket management)
RETRY_LOGIC: Reset Health → Power Cycle + Reset Health → Escalate
MAX_ATTEMPTS: 2 reset-health cycles
```

## Open Questions

| # | Question |
|---|---|
| 1 | ~~How to poll Geneva Action status programmatically?~~ **Resolved**: Use `await acis.submit()` to get `response['id']`, then `await acis.get_result(extension_name, response_id, wait_for_completion=True)`. See coding ability `geneva-action-call`. |
| 2 | What is the expected wait time between reset health and checking node state? |
| 3 | Complete fault code → recovery mapping (only FC 8, 70007, 43030 are documented) |
| 4 | Is PutNodeIntoMOS ever needed in the CSM quorum scenario, or only for DU? |
| 5 | How to check if a GDCO ticket already exists for a node programmatically? |
| 6 | Complete mapping of OFR fault codes → 60k series equivalents? |
