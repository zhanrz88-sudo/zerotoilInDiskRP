# Step 4h — MonitorUpgradeBatchProgressOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [MonitorUpgradeBatchProgressOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/MonitorUpgradeBatchProgressOperation.md)
> **Maps to**: `_step_4h_monitor_upgrade_batch_progress()`
> **Sample incident**: 486860675

## Purpose

State of machines in the active upgrade batch (UD or FD) is unhealthy. XKulfi holds the rollout until enough machines recover. Triage = check XTS watchdog errors per machine, smoke history; escalate to XSSE for hardware, or Fabric Master TSG for smoke.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `domain` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `unhealthy_machines` | `list[str]` | E.g., `BN2CPF327D59C99`, ... |
| `mitigation_summary` | `str` | Triage packet + skip-config row |

## Processing Logic

1. Parse `unhealthy_machines` from `dgrep_rows` / Troubleshooting info.
2. Triage instruction set:
   - Check watchdog errors in **XTS** for each machine.
   - If XStore role unresponsive → suggest restart (manual).
   - If hardware/machine error → escalate to **XSSE**.
   - Check smoke test history (XDS UI) — if smoke is failing, follow Fabric "Master TSG".
3. Oncall path: trigger manual repair (per [eng.ms triggermanualrepair link](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/xpfdeployment/xkulfi/operation_document/triggermanualrepair)) or escalate to XSSE for node recovery.
4. Skip-config row template:

   | PartitionKey | RowKey | DeploymentId | Value | UpdatedBy |
   |---|---|---|---|---|
   | `<tenant>` | `MonitorUpgradeBatchProgressOperation.RetryCountBeforeSkip \| AppRollout \| <domain>` | `<deployment_id>` | `10` | `<alias>` |

   **Manual insert only.**

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - xds-api-call (smoke test status — verify which API)
  - GAP: no coding ability for XTS watchdog errors per machine (Fabric XTS API)
  - GAP: no coding ability for "Trigger manual repair" (Geneva Action / Fabric API)
  - GAP: DynamicSettingConfig write (manual)
AUTOMATABLE: Partially (machine-list extraction + smoke history if API exists).
MANUAL_FALLBACK: Escalate to XSSE for hardware; XStore/Deployment for skip approval.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Which API exposes XTS watchdog errors per machine? Geneva Action, Fabric REST, or Kusto? |
| 2 | Does `xds-api-call` cover smoke history retrieval (last N runs + failing case names)? |
| 3 | "Trigger manual repair" — is there a sanctioned Geneva Action or is it always an XSSE handoff? |
