# Change Note: DGrep Retry and FailoverPendingTransaction Dry-Run Mode

**Date:** 2026-04-28
**Author:** zhdon (with Copilot)
**Commit(s):** Pending
**TSG / Component:** `zerotoil/core/framework.py`, `zerotoil/tsgs/failover_pending_transaction.py`

---

## Why (Motivation)

- **Root cause / trigger:** A backend XJupyterLite run for incident `786460728` succeeded at the notebook level but Step 2 failed to gather DGrep completion evidence because DGrep returned HTTP 503 throttling: `Reached maximum number of outstanding queries from this client (200)`.
- **Impact if not fixed:** Real incident runs could fail after Step 1's chunked DGrep search saturates DGrep outstanding-query quota. Operators would lose Step 2 completion checks, Step 3 stage evidence, and later branch-specific investigation.
- **Related incidents:** `786460728`.
- **Safety request:** The user asked for a TSG dry-run mode so backend validation can run against real incidents and production tenants without updating incidents, transferring ownership, or mitigating.

## Where (Files Changed)

| File | Type | Summary |
|------|------|---------|
| `zerotoil/core/framework.py` | Modified | Added `dgrep_query_with_retry()` and `TsgBase(dry_run=False)` framework support. |
| `zerotoil/tsgs/failover_pending_transaction.py` | Modified | Replaced direct DGrep calls with retry helper, added chunk pacing, and guarded all ICM writes in dry-run mode. |
| `tests/tsgs/test_failover_pending_transaction.py` | Modified | Patched sleeps for fast unit tests and added dry-run coverage. |
| `docs/core_framework.md` | Modified | Documented dry-run semantics and DGrep retry helper. |

## What (Major Logic)

### Change 1: DGrep retry abstraction

The new `dgrep_query_with_retry()` helper centralizes retry behavior for DGrep calls. It retries only known transient/throttle failures (`503`, `429`, `ServiceUnavailable`, `throttl`, and the DGrep outstanding-query quota message), with exponential backoff. Non-throttle exceptions still fail fast.

All DGrep queries in `FailoverPendingTransaction` now go through this helper:

1. Step 1 alert extraction (`ServiceBackgroundActivityEvent`)
2. Step 2 completion check (`AccountFailoverEvent`)
3. Step 3 stage statistics (`AccountFailoverStatisticsEvent`)
4. Step 3 fallback statistics query

Step 1 also waits briefly between chunked DGrep queries to avoid immediately re-saturating the per-client outstanding query quota.

### Change 2: Read-only dry-run mode

`TsgBase` now accepts `dry_run=True`. The base runner prints `[DRY-RUN]`, and the TSG checks `self.dry_run` before any mutating ICM action.

Dry-run still performs read operations:

- ICM incident fetch for input extraction
- DGrep searches
- XDS log searches
- XDS API/Kusto reads
- account metadata lookup

Dry-run skips write operations:

- `incident.add_description(...)`
- `incident.transfer(...)`
- `incident.mitigate(...)`

Instead, the report prints the evidence, transfer target, mitigation reason, or manual action that would have been posted.

### Change 3: Unit tests remain fast

The Step 1 chunk pacing adds real `asyncio.sleep()` calls in production. Unit tests patch `asyncio.sleep` to an instant coroutine so mocks still run quickly and do not perform real waiting.

## Validated

- [x] Unit tests pass (`62` tests, `3` new dry-run tests)
- [x] Existing FailoverPendingTransaction tests remain mocked; no real DGrep, XDS, or ICM access occurs in unit tests
- [x] Dry-run completed path skips `add_description` and `mitigate`
- [x] Dry-run escalation path skips ICM writes and does not raise manual-action exceptions that would stop exploratory runs
- [x] **Backend dry-run validation against real incident 786460728**: TSG completed in 309.1s, DGrep retry recovered Step 2 from one HTTP 503 throttle, all ICM writes skipped, RSRP fallback fired. See [validation report](assets/2026-04-28-dryrun-validation-786460728.md).

## Pending / Open Questions

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | Backend dry-run validation | ✅ Done | See validation report. |
| 2 | Retry tuning | Medium | Current backoff values are conservative. If DGrep remains throttled, increase Step 1 chunk pacing or reduce query fan-out. |
| 3 | Framework-wide write helpers | Low | Future TSGs could use shared helper methods for dry-run ICM write patterns to reduce duplicated guard code. |
| 4 | **PreProd account metadata gap (backend `xstore` only)** | High | Backend `xstore.get_account` (older XJupyterLite image) only consults the XDS account metadata service and raises `StorageAccountNotFoundError` for accounts like `dunghnsfailoversrc1` that exist in Kusto but not XDS. Local `zero-toil/.venv` ships a newer version that falls back to Kusto via the XPortal REST API and resolves the same account fine. **Correct fix is to upgrade the backend `xstore` image** so it uses the same code path as local `.venv`. There is *no* TSG-side workaround: SRP/RSRP tenants are control-plane and cannot host XDS log searches, so substituting them for the storage tenant is forbidden (verified — backend run `66643a65-ca79-4a53-9877-b3b599118d44` returned HTTP 500 `EndpointNotFoundException` on every `xds.search_log("RSRPPublicPreprodEastUS2", ...)` call). When `get_account` fails, the TSG correctly falls back to the existing 'no storage tenant' branch and escalates. |
| 5 | Real `dry_run=False` run after gap #4 fix | Medium | Once the backend image is updated, do one more `dry_run=True` run to confirm Branch A now searches XDS logs on the real storage tenant, then a controlled `dry_run=False` run with a chosen incident. |
| 6 | Update `storage-account-tenant-metadata` and `xds-log-search` coding abilities | ✅ Done | Both abilities now explicitly call out backend-vs-local `get_account` divergence and the SRP-tenant-is-not-a-storage-tenant rule (with the exact HTTP 500 / `EndpointNotFoundException` failure mode). |

## Assets

- Pre-fix backend report showing DGrep throttling (Step 2 fails with HTTP 503 outstanding-query quota): https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=24dd869d-f632-49d9-8f72-3e897fc40d68_temp_run.html
- [Dry-run validation report — incident 786460728](assets/2026-04-28-dryrun-validation-786460728.md) — full before/after comparison
- Backend introspection of `get_account` (proves the local-vs-backend version skew): https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=9f7b3746-e941-42a1-83d6-4e7b4e3ca31b_temp_run.html

### Backend job submissions

| Date (UTC) | Job ID | dry_run | Incident | Package | Outcome | Report |
|------------|--------|---------|----------|---------|---------|--------|
| 2026-04-28 11:51 | `24dd869d-f632-49d9-8f72-3e897fc40d68` | False | 786460728 | `0.0.1.dev260428105857` | Throttled (Step 2 503) | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=24dd869d-f632-49d9-8f72-3e897fc40d68_temp_run.html) |
| 2026-04-28 11:51 | `b8d607ee-4fb0-4272-bd8c-51049c514f90` | True | 786460728 | `0.0.1.dev260428115053` | Success (309.1s; throttle retry recovered, `get_account` PreProd gap surfaced) | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=b8d607ee-4fb0-4272-bd8c-51049c514f90_temp_run.html) |
| 2026-04-28 12:16 | `9f7b3746-e941-42a1-83d6-4e7b4e3ca31b` | n/a | n/a (introspection) | `0.0.1.dev260428121618` | Diff confirmed: backend `xstore.get_account` is older / XDS-only | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=9f7b3746-e941-42a1-83d6-4e7b4e3ca31b_temp_run.html) |
| 2026-04-28 12:21 | `66643a65-ca79-4a53-9877-b3b599118d44` | True | 786460728 | `0.0.1.dev260428122040` | **Failed** — bad fallback used SRP tenant for `xds.search_log`, returned HTTP 500 `EndpointNotFoundException`. Code reverted; lesson recorded in coding abilities + agent rules. | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=66643a65-ca79-4a53-9877-b3b599118d44_temp_run.html) |
