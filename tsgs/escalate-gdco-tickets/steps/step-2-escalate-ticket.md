# Step 2 — Escalate ticket

> **Parent TSG**: [escalate-gdco-tickets](../escalate-gdco-tickets.md)
> **Maps to**: `_step_2_escalate_ticket()` method

## Purpose

Escalate the GDCO ticket severity based on the target: Sev2 for customer-impacting outages, or Sev3 Expedite for proactive repairs.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `gdco_ticket_id` | `str` | From Step 1 |
| `icm_incident_id` | `str` | TSG input |
| `target_severity` | `str` | TSG input (`Sev2` or `Sev3-Expedite`) |

## Outputs

| Field | Type | Description |
|---|---|---|
| `escalation_result` | `str` | `sev2_escalated` / `sev3_expedited` |

## Processing Logic

1. **Branch by target severity:**

| Target | Action |
|---|---|
| `Sev2` | Navigate to GDCO ticket → change severity circle to Sev2 → Save. **Requires DRI on bridge.** |
| `Sev3-Expedite` | Execute Geneva Action `GDCOChangeSeverity` with `Expedite Ticket = true`. |

2. **Geneva Action parameters for Sev3 Expedite:**
   ```python
   await acis.submit(
       extension="Sustainability Operations - Safe",
       operation_id="GDCOChangeSeverity",
       params={
           "IncidentId": icm_incident_id,
           "GDCOTicketId": gdco_ticket_id,
           "Severity": "3",
           "ExpediteTicket": "true",
       }
   )
   ```

3. **SLA monitoring:** Sev3 Expedite = 24 hours. If no response, escalate to `mastange@`, `margs@`.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (GDCOChangeSeverity via xportal.acis.submit)
AUTOMATABLE: Partially (Sev3 Expedite fully automatable via Geneva Action; Sev2 requires human bridge commitment)
APPROVAL_GATE: Sev2 escalation requires human confirmation
```

## Open Questions

| # | Question |
|---|---|
| 1 | How to verify that a GDCO ticket has been actioned by the DC? |
