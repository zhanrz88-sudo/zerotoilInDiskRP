# Change Notes

This folder tracks significant changes to the zerotoil package and TSG automation code.

## Format

Each change note follows `TEMPLATE.md`. Name files as `YYYY-MM-DD-short-description.md`.

Attach supporting assets (reports, comparison tables, investigation outputs) under `assets/`.

## Backend job submissions (mandatory tracking)

Whenever a change is validated by submitting a `zerotoil` job to the XJupyterLite backend, **append the submission to the change note's `## Assets` section** with:

- Date (UTC)
- Job ID
- `dry_run` flag (True/False)
- Incident ID under test
- Package version (e.g. `0.0.1.dev260428115053`)
- Report URL (`https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=<job_id>_temp_run.html`)
- One-line outcome (Success / Fail / Throttled / Pending → status)

This keeps a durable trail linking each code change to the backend runs that exercised it. Without it, we lose the history of what was actually validated end-to-end.

## Index

| Date | File | Summary |
|------|------|---------|
| 2026-04-28 | [2026-04-28-failover-gap-fixes.md](2026-04-28-failover-gap-fixes.md) | Critical gap fixes from real incident investigation |
| 2026-04-28 | [2026-04-28-dgrep-retry-dry-run.md](2026-04-28-dgrep-retry-dry-run.md) | DGrep retry helper + FailoverPendingTransaction dry-run mode |
