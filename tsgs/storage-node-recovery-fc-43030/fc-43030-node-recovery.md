# FC 43030 — Storage Node Recovery

> **Source**: [Fault Code - 43030 | Storage Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%2043030%20-%20Node%20Recovery.md&_a=preview)

## Purpose

Recover storage nodes in OFR with fault code 43030 (disk failure). Nodes in FC 43030 are already in OFR state and do not have customer data. Sub-types: missing/wrong disk, persistent memory disk failure, NVDIMM-N issues.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | Calling TSG (storage-node-recovery dispatch) |
| `cluster_id` | `str` | Calling TSG |
| `fault_info` | `str` | Fault details from FcShell / Kusto |

## Outputs

| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `gdco_ticket_created` / `bios_flavor_reset` / `ofr_for_nvdimm` |
| `fault_type` | `str` | `missing_disk` / `persistent_memory` / `nvdimm_n` |

## Steps

### Step 1 — Classify disk fault type

[Step Analysis](steps/step-1-classify-fault-type.md)

Examine `FaultInfo` to determine sub-type:

| Pattern | Fault Type | Mostly Seen In |
|---|---|---|
| `Disks not found`, wrong disk model vs SKU | `missing_disk` | Gen 6X, 7X |
| `PhysicalDrive0`, 16GB/32GB disk | `persistent_memory` | Gen 6X |
| No SAC post | `nvdimm_n` | Gen 5X |

### Step 2 — Execute fault-type-specific mitigation

[Step Analysis](steps/step-2-execute-mitigation.md)

| Fault Type | Action |
|---|---|
| `missing_disk` | Check GDCO Inventory for SKU → compare with `DISKPART> list disk` in PfAgent Shell → OFR with correct model info → **Calls**: [escalate-gdco-tickets](../escalate-gdco-tickets/escalate-gdco-tickets.md) |
| `persistent_memory` | Confirm via Kusto `LogNodeSnapshot` → flip BIOS flavor ([BIOS Flavour Reset TSG](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/sustainability-engineering/sustainability-engineering-documentation/sops/bios/setbiosflavormanually#bios-flavor-reset)) → Repave via `RequestRepairActionFromMRDelegated`. **Requires XSSE DRI approval.** |
| `nvdimm_n` | No SAC post → OFR with FC 60400 + motherboard inspection → vendor checks → if NVDIMM issue → create breakfix ticket. **Calls**: [escalate-gdco-tickets](../escalate-gdco-tickets/escalate-gdco-tickets.md) |

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: kusto-query (LogNodeSnapshot for fault confirmation, dcmInventoryComponentDiskWmi for disk info), geneva-action-call (RequestRepairActionFromMRDelegated for Repave)
TSG_CALL: escalate-gdco-tickets (for GDCO ticket creation/escalation)
AUTOMATABLE: Partially (fault classification from Kusto automatable; BIOS reset requires XSSE approval; GDCO ticket creation/escalation partially automatable; PfAgent Shell for DISKPART is manual)
MANUAL_FALLBACK: DRI uses DCM Explorer for DISKPART, GDCO Inventory for SKU, Geneva Actions for repave.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can DISKPART output be obtained programmatically from node? |
| 2 | Can BIOS flavor reset be executed via Geneva Action or API? |
| 3 | How to match SKU to expected disk models programmatically? |
