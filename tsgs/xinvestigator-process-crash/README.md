# XInvestigator Process Crash TSG Family

This folder contains TSGs for handling **"Role Process Crash"** incidents, where an XInvestigator worker role crashes frequently (e.g., 16+ times in 60 minutes).

## TSG Call Graph

```
xinvestigator-process-crash  (TSG class)
  Step 1 — Query crash logs from DGrep
  Step 2 — Analyze error pattern
  Step 3 — Check for recent deployments
  Step 4 — Route to mitigation (smoke test mitigation or escalation)
  Step 5 — Document and follow up
```

## Design Principles

- **One source document = one TSG class.** All steps come from the same user-provided TSG document. Steps are methods of one class, not separate classes.
- **No sub-TSGs.** The entire TSG is a single source document; there is no separate referenced document that warrants a sub-TSG class.
- **Step analysis files** under `steps/` provide per-step automation readiness assessment, I/O, and detailed logic — but each step is a method, not a class.
- Shared reference data (contacts, dashboards, deployment pipelines) lives in `_references.md`.

## File Structure

| File | Role |
|---|---|
| `xinvestigator-process-crash.md` | **TSG** — main class with 5 steps as methods |
| `_references.md` | Shared constants (pipelines, smoke test settings, contacts) |
| `steps/step-1-query-crash-logs.md` | Step analysis for Step 1 |
| `steps/step-2-analyze-error-pattern.md` | Step analysis for Step 2 |
| `steps/step-3-check-deployment.md` | Step analysis for Step 3 |
| `steps/step-4-route-mitigation.md` | Step analysis for Step 4 |
| `steps/step-5-document-followup.md` | Step analysis for Step 5 |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `xinvestigator-process-crash.md` | User-provided TSG content (XInvestigator Process Crash TSG) |
| `_references.md` | Aggregated from all sections of the same source |
