# Escalate GDCO Tickets

> **Source**: [Escalate GDCO Tickets](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Escalate%20GDCO%20Tickets.md&_a=preview)

## Purpose

Escalate a GDCO datacenter ticket to get hardware repairs prioritized. This is a **shared/reusable TSG** called by any recovery TSG that needs datacenter intervention.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `icm_incident_id` | `str` | Parent ICM incident |
| `gdco_ticket_id` | `str \| None` | Existing GDCO ticket (if known) |
| `target_severity` | `str` | `Sev2` or `Sev3-Expedite` |
| `node_id` | `str` | Node being repaired |
| `fault_description` | `str` | Clear, actionable description for DC technicians |

## Outputs

| Field | Type | Description |
|---|---|---|
| `gdco_ticket_id` | `str` | GDCO ticket ID (linked or created) |
| `escalation_result` | `str` | `sev2_escalated` / `sev3_expedited` / `ticket_linked` |

## Steps

### Step 1 — Link or create GDCO ticket

[Step Analysis](steps/step-1-link-or-create-ticket.md)

From ICM → **Mitigation and Resolution** tab → link an existing GDCO ticket **or** create a new one → **Save**.

**Ticket quality requirements** (technicians need actionable info):

- **Good**: *"A disk is failing and preventing a Storage node from coming online. Please replace this drive. Model: SEAGATE ST16000NM007G, Serial: ZL2N4RF30000C2179KAC"*
- **Bad**: *"PhysicalDrive is reporting bad. Please investigate"*

For OFR tickets generated via standard signal, follow [Standard Signal requirements](https://microsoft-my.sharepoint.com/:w:/r/personal/mastange_microsoft_com/_layouts/15/Doc.aspx?sourcedoc=%7B595B0213-D5EF-4F35-ACC5-1E4783FFEF00%7D).

### Step 2 — Escalate based on target severity

[Step Analysis](steps/step-2-escalate-ticket.md)

#### Path A: Escalate to Sev2 (customer impact occurred or imminent)

> **Requirement**: A DRI must be on the bridge for the entire duration the DC is engaged.

1. Navigate to the GDCO ticket.
2. Click the severity circle → change from Sev3 to **Sev2** → **Save**.
3. An email from **OMC** will be sent to confirm impact.

#### Path B: Sev3 Expedite (no immediate customer impact)

**Option 1 — Geneva Action** (preferred for automation):

| Parameter | Value |
|---|---|
| OperationId | `GDCOChangeSeverity` |
| Group | `Sustainability Operations - Safe` |
| Incident ID | `<icm_incident_id>` |
| GDCO Ticket ID | `<gdco_ticket_id>` |
| Severity | `3` |
| Expedite Ticket | `true` |

**Option 2 — GDCO App UI**:
1. Open GDCO ticket → click severity circle.
2. Check **Expedite** box → accept terms → **Save**.

**SLA**: Sev3 Expedite = **24 hours**. If no response within 24h, contact manager, Jake (`mastange@`), Margaret (`margs@`).

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (GDCOChangeSeverity for Sev3 Expedite)
AUTOMATABLE: Partially (Sev3 Expedite via Geneva Action; Sev2 requires bridge commitment)
APPROVAL_GATE: Sev2 escalation should require human confirmation
```

## Open Questions

| # | Question |
|---|---|
| 1 | Can GDCO tickets be created programmatically, or only linked from ICM UI? |
| 2 | ~~Is the `GDCOChangeSeverity` Geneva Action callable via API?~~ **Resolved**: Yes — `await acis.execute("Sustainability Operations - Safe", "GDCOChangeSeverity", [incident_id, gdco_ticket_id, severity, expedite])` via `xportal.acis`. See coding ability `geneva-action-call`. |
| 3 | How to verify that a GDCO ticket has been actioned by the DC? |
