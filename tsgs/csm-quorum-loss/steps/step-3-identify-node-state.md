# Step 3 — Identify node state for each offline CSM

> **Parent TSG**: [csm-2-failures-from-quorum-loss](../csm-2-failures-from-quorum-loss.md)
> **Maps to**: `_step_3_identify_node_state()` method

## Purpose

For each offline CSM node, determine its fabric state (HI, OFR, Ready, etc.) and fault information.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `offline_csms` | `list[dict]` | From Step 1 (each with `node_id`) |
| `cluster_name` | `str` | Derived from tenant (e.g., `DUB07PrdStr12`) |
| `cloud_environment` | `str` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `node_states` | `list[dict]` | Per-node: `node_id`, `node_state` (HI/OFR/Ready/Other), `fault_code`, `fault_reason`, `fault_time`, `ofr_fault_code`, `ofr_fault_reason` |

## Processing Logic

1. **Query node state via Kusto** (automatable path):

```kusto
GetAllStorageNodeFabricHealth
| where NodeId contains "<node_id>"
| project ClusterId, Tenant, NodeId, TMState, DCMState,
          HIFault, HIFaultReason, HIFaultTime,
          OFRFaultCode, OFRFaultReason
```

   Kusto endpoints: see `_references.md`.

2. **Parse state** — Map: `TMState` → `node_state`, `HIFault` → `fault_code`, `HIFaultReason` → `fault_reason`, `HIFaultTime` → `fault_time`, `OFRFaultCode` → `ofr_fault_code`, `OFRFaultReason` → `ofr_fault_reason`.

3. **Warn if Kusto data may be stale** — If node shows as `Ready` but parent TSG identified it as offline, warn and recommend FcShell/DCM Explorer manual verification.

**Alternative (manual):** FcShell for real-time data:
```powershell
$f = Get-Fabric <ClusterName>
$n = $f | Get-Node "<NodeId>"
$n                    # Shows state
$n.FaultInfo          # HI fault details
$n.DCMNode.NLMResource.RmaInfo  # OFR details
```

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: kusto-query (xportal.kusto.query), xds-api-call (RoleInstancesApi for supplemental role-level health)
AUTOMATABLE: Yes (Kusto path; XDS ping as supplemental validation)
MANUAL_FALLBACK: FcShell / DCM Explorer for real-time data
```

## Open Questions

| # | Question |
|---|---|
| 1 | How stale is Kusto data typically? (minutes? hours?) |
| 2 | Is there an API to FcShell that could be called programmatically? |
| 3 | Do we need the full `faultInfo` JSON or just the parsed fields? |
