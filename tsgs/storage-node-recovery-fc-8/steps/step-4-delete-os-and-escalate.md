# Step 4 — Delete OS images in MOS and escalate

> **Parent TSG**: [fc-8-node-recovery](../fc-8-node-recovery.md)
> **Maps to**: `_step_4_delete_os_and_escalate()` method

## Purpose
Last-resort recovery: delete OS images in MOS to force PfAgent restart. If that fails, check PfAgent version and escalate or send to OFR.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |
| `cluster_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `recovery_result` | `str` | `recovered` / `sent_to_ofr` / `escalated_to_team` |

## Processing Logic
1. Boot into MOS → PfAgent Shell → `cd C:\OS` → `del *`.
2. Redeploy FullOS. If recovers → done.
3. If still stuck: query PfAgent version via Kusto:
   ```kusto
   cluster('azuredcm.kusto.windows.net').database('AzureDCMDb').RdmResourceProperty
   | where Property has "PFAgent.Version" and ResourceId == "<node_id>"
   | summarize arg_max(PreciseTimeStamp, *) by ResourceId
   | project PfAgentVersion=Value, NodeId=ResourceId
   ```
4. If PfAgent version < `132.879.3974.3` → known issue, repeat OS delete while waiting for fleet update.
5. If PfAgent version is current: compile evidence, escalate to Titan Agents Team.
6. If no systemic cause: send to OFR via `RequestOFRFromMRWithOverride`.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: geneva-action-call (PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated, RequestOFRFromMRWithOverride), kusto-query (RdmResourceProperty for PfAgent version)
AUTOMATABLE: Partially (PfAgent version check automatable; OS deletion requires SAC Shell; OFR action automatable)
MANUAL_FALLBACK: DRI uses PfAgent Shell in DCM Explorer for OS deletion, Kusto for version check.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can PfAgent Shell commands be executed via API? |
| 2 | Is the PfAgent version threshold still `132.879.3974.3` or has it been updated? |
