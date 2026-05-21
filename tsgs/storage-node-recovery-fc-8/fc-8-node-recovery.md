# FC 8 — Storage Node Recovery

> **Source**: [Fault Code - 8 | Storage Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%208%20-%20Node%20Recovery.md&_a=preview)

## Purpose

Recover storage nodes stuck in HumanInvestigate with fault code 8. FC 8 is a generic fault code — possible causes include motherboard issues, DAC cable problems, and PfAgent failures. This TSG progressively escalates recovery actions from simple reboot to OS reimage to OFR.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | Calling TSG (storage-node-recovery dispatch) |
| `cluster_id` | `str` | Calling TSG |
| `tenant_name` | `str` | Calling TSG |

## Outputs

| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `recovered` / `sent_to_ofr` / `escalated_to_team` |
| `actions_taken` | `list[str]` | Recovery actions attempted in sequence |

## Steps

### Step 1 — Verify network connectivity and SAC responsiveness

[Step Analysis](steps/step-1-verify-connectivity.md)

1. **Network check** (DCM Explorer → Resource Details → Operations → Network tab): verify `Port Isolation State = Enable` and `Link Active State = Connected`. If disconnected → send to OFR.
2. **SAC check** (DCM Explorer → SAC tab → Connect): wait for `SAC>` prompt. If no prompt → send to OFR.
3. **IP check**: run `i` at SAC prompt. If IP starts with `169.` (APIPA) → skip to Step 3 (MOS).
4. **Channel check**: run `ch`. If channels missing → reboot → if still missing → send to OFR.

### Step 2 — Simple recovery (Reboot and Reset Health)

[Step Analysis](steps/step-2-simple-recovery.md)

Check that affected nodes are not all in the same rack (power/TOR issue). Then:

1. Power Off → `PowerNodeWithSafetyChecksDelegated`
2. Reset Health → `ResetNodeHealthWithSafetyChecksCrossServiceDelegated`
3. Power On → `PowerNodeWithSafetyChecksDelegated`

If node recovers to Ready → **done**. If falls back to HI → continue.

### Step 3 — Boot into MOS and redeploy OS

[Step Analysis](steps/step-3-mos-recovery.md)

1. Boot node into MOS via `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated`.
2. Check DCM Agent status via SAC. Restart RdAgent if needed.
3. Redeploy FullOS via `RequestRepairActionFromMRDelegated`.
4. Monitor recovery. If falls back to HI with FC 8 or FC 10033 → continue. If new FC → dispatch to that FC's TSG.

### Step 4 — Delete OS images in MOS and escalate

[Step Analysis](steps/step-4-delete-os-and-escalate.md)

1. Boot into MOS → connect PfAgent Shell → navigate to `C:\OS` → `del *`.
2. Redeploy FullOS. If recovers → **done**.
3. If still stuck: check PfAgent version (versions < `132.879.3974.3` have known issues). If old PfAgent → repeat step above while waiting for fleet update.
4. If no PfAgent issue: compile evidence, escalate to Titan Agents Team or send to OFR via `RequestOFRFromMRWithOverride`.

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (PowerNodeWithSafetyChecksDelegated, ResetNodeHealthWithSafetyChecksCrossServiceDelegated, PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated, RequestRepairActionFromMRDelegated, RequestOFRFromMRWithOverride), kusto-query (GetAllStorageNodeFabricHealth, RdmResourceProperty for PfAgent version)
TSG_CALL: escalate-gdco-tickets (if node sent to OFR and needs GDCO ticket)
AUTOMATABLE: Partially (Steps 1-2 network/SAC checks require DCM Explorer UI; Geneva Actions for Reset/Power automatable with approval; MOS operations and OS deletion require SAC/Shell access which is not yet automatable)
MANUAL_FALLBACK: DRI uses DCM Explorer for SAC, FcShell for node state, Geneva Actions portal for recovery.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can DCM Explorer SAC connectivity check be done programmatically? |
| 2 | Can PfAgent Shell commands (navigate, delete files) be executed via API? |
| 3 | What is the exact PfAgent version threshold that indicates a known issue? (Source says < `132.879.3974.3` as of April 2024) |
| 4 | How to programmatically check if nodes are co-located in the same rack? |
