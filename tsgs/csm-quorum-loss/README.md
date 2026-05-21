# CSM Quorum Loss TSG Family

This folder contains TSGs for handling the **"CSM 2 Failures Away from Quorum Loss"** incident.

## TSG Call Graph

```
csm-2-failures-from-quorum-loss  (TSG class)
  Step 1 — Identify offline CSMs
  Step 2 — Check deployment status
  Step 3 — Identify node state for each offline CSM
  Step 4 — Recover nodes by state
    ├── [calls TSG] escalate-gdco-tickets  (separate folder)
    └── [calls TSG] storage-node-recovery  (separate folder)
  Step 5 — Post-mitigation
```

## Design Principles

- **One source document = one TSG class.** The main TSG corresponds to the CSM Quorum Loss KB document.
- **Every called TSG lives in its own folder.** No distinction between "sub-TSG" and "external TSG" — all called TSGs are peers in `zero-toil/tsgs/`.
- **Step analysis files** under `steps/` provide per-step automation readiness assessment, I/O, and detailed logic.
- Shared reference data (contacts, dashboards, Kusto endpoints) lives in `_references.md`.

## File Structure

| File | Role |
|---|---|
| `csm-2-failures-from-quorum-loss.md` | **TSG** — main class with 5 steps as methods |
| `_references.md` | Shared constants (endpoints, actions, contacts) |
| `steps/step-1-identify-offline-csms.md` | Step analysis for Step 1 |
| `steps/step-2-check-deployment-status.md` | Step analysis for Step 2 |
| `steps/step-3-identify-node-state.md` | Step analysis for Step 3 |
| `steps/step-4-recover-nodes.md` | Step analysis for Step 4 |
| `steps/step-5-post-mitigation.md` | Step analysis for Step 5 |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `csm-2-failures-from-quorum-loss.md` | [CSM Quorum Loss TSG](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/CSM%20Quorum%20Loss%20TSG.md&_a=preview) |
| `_references.md` | Aggregated from all sources |
