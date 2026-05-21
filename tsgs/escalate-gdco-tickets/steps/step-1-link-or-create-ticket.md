# Step 1 — Link or create GDCO ticket

> **Parent TSG**: [escalate-gdco-tickets](../escalate-gdco-tickets.md)
> **Maps to**: `_step_1_link_or_create_ticket()` method

## Purpose

Link an existing GDCO ticket to the ICM incident, or create a new one with actionable repair information.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `icm_incident_id` | `str` | TSG input |
| `gdco_ticket_id` | `str \| None` | TSG input (existing ticket if known) |
| `node_id` | `str` | TSG input |
| `fault_description` | `str` | TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `gdco_ticket_id` | `str` | GDCO ticket ID (linked or created) |

## Processing Logic

1. From ICM → **Mitigation and Resolution** tab → link existing GDCO ticket or create new one.
2. Ensure ticket contains actionable information for DC technicians (model, serial, specific repair action).
3. Click **Save**.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: icm-get-incident (Incident — access Mitigation and Resolution)
AUTOMATABLE: No (GDCO ticket creation/linking via ICM UI only — no known programmatic API)
MANUAL_FALLBACK: DRI links/creates ticket via ICM portal UI.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can GDCO tickets be created programmatically, or only linked from ICM UI? |
