# Step 5 — Post-mitigation

> **Parent TSG**: [csm-2-failures-from-quorum-loss](../csm-2-failures-from-quorum-loss.md)
> **Maps to**: `_step_5_post_mitigation()` method

## Purpose

Monitor recovery, handle self-mitigation behavior, and ensure continued follow-up on remaining offline CSMs.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `recovery_results` | `list[dict]` | From Step 4 |
| `cloud_environment` | `str` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `follow_up_needed` | `bool` | Whether remaining nodes still need recovery |
| `follow_up_notes` | `str` | Guidance for continued recovery |

## Processing Logic

1. The monitor self-mitigates after **120 minutes** of healthy status.
2. Even if ICM self-mitigates, **continue driving recovery** of remaining offline CSMs.
3. **Public**: XSSE DRI + Ops own follow-up.
4. **AGC**: XSSE team members must be alerted.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: icm-get-incident (Incident.add_description — document recovery status)
AUTOMATABLE: Partially (monitoring can be automated; continued recovery requires human judgment)
MANUAL_FALLBACK: DRI monitors CSM health dashboard and continues driving node repairs.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Self-mitigation monitor metric path in Geneva — needed to detect re-alert risk |
