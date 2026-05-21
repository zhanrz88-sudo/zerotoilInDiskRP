# FailoverPendingTransaction - PrimaryStuck.PrepareFailover

## TSG Call Graph

```text
failover-pending-transaction-primary-stuck-prepare-failover  (TSG class)
  Step 1 — Extract failover context from alert
  Step 2 — Check failover completion
  Step 3 — Determine stuck stage and side
  Step 4 — Diagnose known issues and mitigate or escalate
    ├── [Branch A] PrepareFailover stuck → XDS log diagnosis → ICM transfer (StorageCRM / TableMaster)
    ├── [Branch B] PollFailover stuck on Secondary → GeoConfigOff → RA ximi
    └── [Branch C] Default → RA xgeo DRI
  Step 5 — Update incident and close triage loop
```

## Design Principles

- **One source document = one TSG class.** The main TSG corresponds to the single KB document.
- **Steps are methods, not separate classes.** All diagnostic branches in Step 4 are inline logic.
- **No sub-TSG calls.** All mitigations are ICM transfers to owning teams, not automated Geneva Actions.
- **Step analysis files** under `steps/` provide per-step automation readiness assessment.
- Keep all operational constants and links in `_references.md`.

## File Structure

| File | Role |
|---|---|
| `failover-pending-transaction-primary-stuck-prepare-failover.md` | **TSG** — main class with 5 steps as methods |
| `_references.md` | Shared constants (endpoints, actions, contacts) |
| `steps/step-1-extract-failover-context.md` | Step analysis for Step 1 |
| `steps/step-2-check-failover-completion.md` | Step analysis for Step 2 |
| `steps/step-3-determine-stuck-stage.md` | Step analysis for Step 3 |
| `steps/step-4-mitigate-or-escalate.md` | Step analysis for Step 4 |
| `steps/step-5-update-incident.md` | Step analysis for Step 5 |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `failover-pending-transaction-primary-stuck-prepare-failover.md` | [[FailoverPendingTransaction] Failover for accounts stuck on PrimaryStuck.PrepareFailover in XXX](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/%5BFailoverPendingTransaction%5D%20Failover%20for%20accounts%20stuck%20on%20PrimaryStuck.PrepareFailover%20in%20XXX.md&_a=preview) |
| `_references.md` | Aggregated constants from all sources above |