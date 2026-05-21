# Step 4z — Generic escalation

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Maps to**: `_step_4z_generic_escalation()`

## Purpose

Fallback when the operation isn't covered by a per-operation branch (e.g., `TenantHealthSignOffOperation`, `CheckOSVersionMismatchedOperation`, `UpdateConfigurationStorageVersionOperation`, `UpdateDynamicConfigSchemaOperation`, `ResetWatchdogConfigOperation`, `CheckLeftOverMachinesBeforeUnbookOperation`, `ClearPastRolloutAlertsOperation`) — or when Step 1 failed to parse.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `str` | TSG input |
| `tenant`, `operation`, `rollout_type`, `deployment_id`, `domain`, `target_version` | `str \| None` | Step 1 (any may be `None`) |
| `dgrep_link` | `str` | Step 2 |
| `history_xml_path` | `str` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `escalation_packet` | `dict` | Structured evidence package for the oncall page |
| `mitigation_summary` | `str` | Plain-text version of the packet for ICM discussion |

## Processing Logic

1. Build the evidence package:
   - Incident id + title
   - Parsed fields (or `None`)
   - DGrep link
   - Blob history path: `xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/<operation>` (when `tenant` and `operation` known)
   - Generic skip-config template (pattern: `<Operation>.RetryCountBeforeSkip | <RolloutType>` or `... | <Domain>`) — annotated as "do not apply without lease-owner approval"
2. Page `XStore/Deployment` oncall during Redmond hours; otherwise notify `yazzhang` (Shanghai).
3. Return packet as `mitigation_summary`.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - icm-get-incident (post evidence package as discussion)
AUTOMATABLE: Yes (packet rendering + ICM comment only; no mutating action).
MANUAL_FALLBACK: n/a — this is the fallback.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is there a way to look up the current XStore/Deployment oncall from ICM/IcM Routing so the packet can `@mention` the right alias automatically? |
| 2 | Should we write per-operation stubs for the operations listed above (currently grouped under generic) once we observe real incidents for them? |
