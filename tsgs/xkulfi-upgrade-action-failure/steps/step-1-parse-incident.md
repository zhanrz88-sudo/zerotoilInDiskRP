# Step 1 — Parse incident

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Maps to**: `_step_1_parse_incident()`

## Purpose

Extract the structured fields from the ICM incident title (and description, if needed) so subsequent steps can route and query.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `incident_id` | `str` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `tenant` | `str` | Tenant name (or virtual tenant for ZRS) |
| `operation` | `str` | UpgradeAction operation name |
| `rollout_type` | `str` | `ApServiceRollout` \| `AppRollout` \| `OsUpgrade` |
| `deployment_id` | `str` | Group rollout id, e.g. `01DA89CBF0EC9A0B:11647` |
| `domain` | `str \| None` | UD/FD identifier (e.g., `UpgradeDomain=2`) |
| `target_version` | `str \| None` | E.g., `RELEASE_STG95/95.9.33.0` (when present) |
| `app` | `str \| None` | App name for AP rollout form (e.g., `APP~CEG_AZUREPIE-AZURECHAOSAGENT-VE`) |
| `dgrep_tenant` | `str \| None` | Tenant for DGrep Query (e.g., `XKulfiEastUS-Prod-BL2P`) |
| `alert_keyword` | `str \| None` | Alert Keyword (e.g., `Upgrade action SmokeTestOperation for [[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z]`) |

## Processing Logic

1. Pull the incident via `icm-get-incident` and read `title` (fallback to `description`).
2. Try the patterns below in order; first match wins. Use the named groups verbatim.

   - **Domain-level new format**:
     ```
     \[(?P<operation>\w+)=\[\[XKulfi\](?P<tenant>[^\-]+)-(?P<rollout_type>ApServiceRollout|AppRollout|OsUpgrade)-(?P<deployment_id>[0-9A-F]+:\d+)\]\[(?P<target_version>[^\]]+)\]\[UpgradeDomain=(?P<domain>\d+)\]\[(?P<ts>[^\]]+)\]\]
     ```
   - **Deployment-level new format** (no domain):
     ```
     \[(?P<operation>\w+)=\[\[XKulfi\](?P<tenant>[^\-]+)-(?P<rollout_type>ApServiceRollout|AppRollout|OsUpgrade)-(?P<deployment_id>[0-9A-F]+:\d+)\]\]
     ```
   - **AP rollout `[OperationName=...][ActionKey=Tenant;DeploymentId;App;Version]`**:
     ```
     \[OperationName=(?P<operation>\w+)\]\[ActionKey=(?P<tenant>[^;]+);(?P<deployment_id>[0-9A-F]+:\d+);(?P<app>[^;]+);(?P<target_version>[^\]]+)\]
     ```
     `rollout_type` from a sibling token `[RepairKind=...]`.
   - **Legacy short form** `[Operation=DeploymentId]`:
     ```
     \[(?P<operation>\w+)=(?P<deployment_id>[0-9A-F]+:\d+)\]
     ```
     Tenant must be parsed from a separate `[Tenant=...]` token or the title prefix `<Tenant> Raising Alert`. `domain`/`target_version` = `None`.
3. If no pattern matches → return `operation=None` (Step 3 will route to step-4z).
4. Retrieve dgrep_tenant from incident description, search the key value pair like 'Icm.RaisingLocation	XKulfiEastUS-Prod-BL2P', where XKulfiEastUS-Prod-BL2P is dgrep_tenant
4. Retrieve alert_keyword from incident description, search the key value pair like 'Message Environment: PROD; Region: East US; XKulfi tenant: XKulfiEastUS-Prod-BL2P; STG virtual tenant: MS-BLZ21PrdStrz27A; STG tenant: MS-BLZ21PrdStr27A; STG tenant kind: XStore; Alert Id: [RepairKind=ApServiceRollout][Version=AP_2026_04_06_5003][OperationName=SmokeTestOperation][ActionKey=[[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z]]; Alert keyword: Upgrade action SmokeTestOperation for [[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z]', where 'Upgrade action SmokeTestOperation for [[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277][APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003][UpgradeDomain=7][2026-04-21T10:31:42Z]' is alert_keyword

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - icm-get-incident (read title/description)
  - GAP: pure regex parsing — no coding ability needed, but the regex set
    above must be unit-tested against the sample incidents listed in
    _references.md before relying on it in production.
AUTOMATABLE: Yes.
MANUAL_FALLBACK: If all regexes miss, attach the raw title to the ICM
discussion and continue with operation=None → step-4z.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is `tenant` in the new format always equal to the physical tenant, or is it sometimes already the virtual tenant for ZRS? Affects which value Step 2 uses for the blob lookup. |
| 2 | Does the legacy short form `[Operation=DeploymentId]` ever appear with a domain in the description body? Need to scan more samples. |
