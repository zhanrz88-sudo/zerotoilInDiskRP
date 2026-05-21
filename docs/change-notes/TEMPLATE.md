# Change Note: [TITLE]

**Date:** YYYY-MM-DD
**Author:** [alias]
**Commit(s):** [commit hash(es)]
**TSG / Component:** [e.g., `zerotoil/tsgs/failover_pending_transaction.py`]

---

## Why (Motivation)

_What triggered this change? Incident investigation, feature request, bug report, code review feedback, etc._

- **Root cause / trigger:** ...
- **Impact if not fixed:** ...
- **Related incidents:** [list incident IDs if applicable]

## Where (Files Changed)

| File | Type | Summary |
|------|------|---------|
| `path/to/file.py` | Modified | Brief description |
| `path/to/test.py` | Modified | Brief description |
| `path/to/new_file.md` | Added | Brief description |

## What (Major Logic)

_Describe the key design decisions and logic changes. Focus on the "why this approach" not just the "what"._

### Change 1: [Title]

...

### Change 2: [Title]

...

## Validated

_What was tested or verified? Include test counts, manual verification, live run results._

- [ ] Unit tests pass (N tests, M new)
- [ ] Ran against real incident(s): [IDs]
- [ ] Code review / rubber-duck critique addressed
- [ ] Existing tests unbroken (no regressions)

## Pending / Open Questions

_What remains unresolved? What needs follow-up?_

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | ... | High/Med/Low | ... |

## Assets

_Links to attached reports, DGrep screenshots, comparison tables, etc._

- [Asset name](assets/YYYY-MM-DD-asset-name.md)

### Backend job submissions

| Date (UTC) | Job ID | dry_run | Incident | Package | Outcome | Report |
|------------|--------|---------|----------|---------|---------|--------|
| YYYY-MM-DD | `<job_id>` | True/False | `<incident_id>` | `0.0.1.dev...` | Success/Fail/Throttled | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=<job_id>_temp_run.html) |
