# Step 2 — Check deployment status

> **Parent TSG**: [csm-2-failures-from-quorum-loss](../csm-2-failures-from-quorum-loss.md)
> **Maps to**: `_step_2_check_deployment_status()` method

## Purpose

Check whether an active deployment (xDep upgrade) is contributing to CSM offline nodes. If it is, decide whether to block the upgrade.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `offline_csm_uds` | `list[int]` | Update domains of offline CSMs (from Step 1) |
| `icm_severity` | `str` | Current incident severity (`Sev2` / `Sev3`) |

## Outputs

| Field | Type | Description |
|---|---|---|
| `deployment_active` | `bool` | Whether a deployment is in progress |
| `deployment_ud` | `int \| None` | Current UD being upgraded |
| `ud_overlap` | `bool` | Whether deployment UD overlaps with an offline CSM UD |
| `upgrade_blocked` | `bool` | Whether the upgrade was blocked |

## Processing Logic

1. **Query upgrade state** — Use `UpgradeStateApi.upgrade_state_get_upgrade_state()` to get `UpgradeState` with `upgrade_status`, `current_domain_id`, `current_domain_type`.

2. **Check UD overlap** — Compare `deployment_ud` against `offline_csm_uds`.
   - Match → deployment may have caused the CSM failure, or CSM slow to recover post-upgrade.
   - No match → CSM failure is independent.

3. **Decide whether to block upgrade:**

| Condition | Action |
|---|---|
| `deployment_active` AND `icm_severity == Sev2` (1 away) | Contact `xdep@microsoft.com` → block upgrade immediately |
| `deployment_active` AND `icm_severity == Sev3` (2 away) | Continue node repairs; avoid repairing nodes in active UD/FD |
| `deployment_active == false` | No action needed |

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: xds-api-call (UpgradeStateApi.upgrade_state_get_upgrade_state, UpgradeStateApi.upgrade_state_is_upgrade_in_progress)
AUTOMATABLE: Partially (read upgrade state = Yes; block upgrade = requires human approval)
SIDE_EFFECT: May send email to xdep@ to block upgrade (gate behind approval)
```

## Open Questions

| # | Question |
|---|---|
| 1 | ~~Can the XDS upgrade state be queried programmatically?~~ **Resolved**: Yes — `UpgradeStateApi.upgrade_state_get_upgrade_state()` returns `UpgradeState` with `upgrade_status`, `current_domain_id`, `current_domain_type`. |
| 2 | How to block deployments in AGC (not yet documented per DU TSG TODO)? |
| 3 | Should we auto-email xdep, or flag for human approval? |
