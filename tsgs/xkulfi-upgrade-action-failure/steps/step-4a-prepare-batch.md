# Step 4a — PrepareBatchOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [PrepareBatchOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/PrepareBatchOperation.md)
> **Maps to**: `_step_4a_prepare_batch()`
> **Sample incident**: 569195691

## Purpose

XDS domain preparation timed out. Identify the stuck XDS task and produce a mitigation packet (Fabric-style triage; Preprod-only "Skip Current Task" if lease owner approves).

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `domain` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `current_xds_task` | `str \| None` | E.g., `CheckQuorumTask::XvExtentManagerRole` (parsed from logs / Troubleshooting info) |
| `mitigation_summary` | `str` | Human-readable next action |

## Processing Logic

1. From `dgrep_rows`, attempt to extract the current XDS task name (string after `Current task:` or in the Troubleshooting info pattern).
2. Mitigation packet:
   - **Always** — link to incident "Retrieve XDS upgrade state".
   - **Treat as Fabric XDS preparation issue** — reuse Fabric deployment knowledge (XDS task on `CheckQuorumTask::*`, `XvExtent*`, etc.).
   - **If Preprod and lease-owner approves** — instruct: open XDS UI ▸ Tenant Status ▸ Upgrade State ▸ Advanced Operations ▸ "Skip Current Task". **Do not click programmatically.**
3. Return `mitigation_summary` containing: tenant, deployment_id, domain, current task, "Skip Current Task" instruction (Preprod only), Fabric XDS task reference.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - GAP: no XDS API to read "Upgrade State / current task" without UI; xds-api-call
    has UpgradeStateApi — verify if it exposes the in-flight prep task name.
AUTOMATABLE: Partially (read-only diagnosis).
  - "Skip Current Task" is UI-only and Preprod-only with manual approval.
MANUAL_FALLBACK: Escalate to XStore/Deployment oncall (Redmond) or yazzhang (Shanghai).
```

## Open Questions

| # | Question |
|---|---|
| 1 | Does `xds-api-call` `UpgradeStateApi` return the name of the currently running preparation task (e.g., `CheckQuorumTask::XvExtentManagerRole`)? If yes, `current_xds_task` becomes deterministically extractable. |
| 2 | Is there a programmatic "Skip Current Task" endpoint that respects the same Preprod gate, or is it strictly UI? |
