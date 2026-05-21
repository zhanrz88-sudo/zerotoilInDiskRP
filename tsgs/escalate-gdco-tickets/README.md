# Escalate GDCO Tickets TSG

## TSG Call Graph

```
escalate-gdco-tickets  (TSG class)
  Step 1 — Link or create GDCO ticket
  Step 2 — Escalate based on target severity
```

## Design Principles

- One source document = one TSG class.
- Steps are methods, not separate classes.
- This TSG is reusable — called by any recovery TSG that needs GDCO ticket escalation.

## File Structure

| File | Role |
|---|---|
| `escalate-gdco-tickets.md` | **TSG** — main class with 2 steps as methods |
| `_references.md` | Shared constants (Geneva Actions, portals, contacts) |
| `steps/step-1-link-or-create-ticket.md` | Step analysis for Step 1 |
| `steps/step-2-escalate-ticket.md` | Step analysis for Step 2 |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `escalate-gdco-tickets.md` | [Escalate GDCO Tickets](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Escalate%20GDCO%20Tickets.md&_a=preview) |
