# Change Note: XDS Time Anchor, Now-Verbose Fallback, Graceful ManualActionRequired

**Date:** 2026-04-29
**Author:** zhdon (with Copilot)
**Commit(s):** Pending
**TSG / Component:** `zerotoil/tsgs/failover_pending_transaction.py`, `tests/tsgs/test_failover_pending_transaction.py`
**Predecessor:** [2026-04-28 DGrep retry + dry-run](2026-04-28-dgrep-retry-dry-run.md)

---

## Why (Motivation)

- **Root cause / trigger:** Backend run `232b307d-6a27-4a83-9ef7-dbcf23193b51` against incident `786460728` showed that all XDS searches in Branch A returned 0 rows. Investigation revealed three independent issues:
  1. **Time window mismatch:** XDS searches were anchored to `incident_start_time_utc` (10:30 UTC), but DGrep alerts for the sampled account fired at 07:36 / 08:11 UTC — a ~3 hour gap. The XDS window completely missed the actual failover activity period.
  2. **Long-stuck failovers have no error logs:** These failovers were initiated months ago (Jun–Oct 2025). They produce no XACServer error / TableMaster error entries. The only XDS signal is in **verbose** logs during active retry windows — but verbose logs have ~2 day retention and the alert-time logs had expired.
  3. **`ManualActionRequired` crashed non-dry-run:** Branch E raised `ManualActionRequired` which propagated as an unhandled notebook exception (`Status=Fail`, `Reason=NotebookException`), preventing Step 5 from posting evidence to the incident.
- **Impact if not fixed:** XDS investigation would always miss signal for incidents where ICM creation lags behind the alert. Long-stuck failovers would never surface verbose evidence. Non-dry-run TSG executions would crash before posting evidence to ICM.
- **Related incidents:** `786460728`.

## Where (Files Changed)

| File | Type | Summary |
|------|------|---------|
| `zerotoil/tsgs/failover_pending_transaction.py` | Modified | (A) XDS time anchor, (B) now-verbose fallback, (E) graceful ManualActionRequired |
| `tests/tsgs/test_failover_pending_transaction.py` | Modified | Updated 12 tests from `pytest.raises(ManualActionRequired)` to assert graceful return |

## What (Major Logic)

### Change A: Anchor XDS searches to DGrep alert timestamp

All XDS branch methods (Branch A, B, D) now prefer `self.alert_timestamp` — the latest `PreciseTimeStamp` from the DGrep alert row for the active candidate — over `tsg_input.incident_start_time_utc`.

- **Source:** Step 1 already captures `sample_timestamp` from each DGrep row. The dedup logic now keeps the **latest** timestamp per deduplicated `operation_id|account_name` key and stores it as `alert_timestamp` on the candidate dict.
- **Parsing:** `_set_active_candidate()` parses `alert_timestamp` into a UTC-aware `datetime` and stores it as `self.alert_timestamp`.
- **Usage:** `event_time = self.alert_timestamp or tsg_input.incident_start_time_utc` in Branch A, B, and D. Falls back gracefully if parsing fails or no timestamp is available.
- **Reporting:** Each branch prints the chosen anchor and its source (`alert_timestamp` vs `incident_start_time_utc`).

### Change B: Supplementary "now" verbose search in Branch A

After the existing XACServer verbose + TableMaster error searches, if **both** returned 0 rows, Branch A now performs a supplementary XACServer verbose search with a `now ±5min` window on each search tenant.

- **Rationale:** Long-stuck failovers continuously retry and produce verbose log entries. Even when alert-time logs have expired (>2 days), the current retry activity is visible.
- **Guard:** Only fires when both alert-time searches returned 0 rows. Uses `top=20` and a 5-minute window (within the coding ability's recommended max for verbose).
- **Non-routing:** Supplementary evidence only. Results are appended to `xds_evidence_summary` with a `[Supplementary]` prefix and added to evidence links, but do **not** influence the Branch A routing logic (LLAM/split pattern matching still operates on the alert-time results only).
- **Error handling:** Wrapped in try/except so a failed "now" search doesn't break the overall flow.

### Change E: Graceful ManualActionRequired handling

`_run()` no longer re-raises `ManualActionRequired`. Instead:

1. The `except ManualActionRequired` block sets `self.mitigation_status = "ManualActionRequired"` and `self.mitigation_detail = str(e)` (if not already set by the branch).
2. Breaks the candidate loop.
3. The `finally` block still records the candidate result.
4. After the loop, `_apply_primary_summary_result()` and Step 5 run normally.
5. Returns a proper `FailoverPendingTransactionOutput` with `mitigation_status="ManualActionRequired"`.

**Contract change:** `run_for_incident()` / `_run()` no longer raise `ManualActionRequired`. Callers (including the published XJPL template) receive a normal output. The manual action details are in `mitigation_status` and `mitigation_detail`.

### Test updates

12 tests updated:
- Removed `with pytest.raises(ManualActionRequired):` wrappers
- Now assert `result.mitigation_status` equals the expected value (e.g., `"ManualActionRequired"`, `"Escalated"`)
- Assert `tsg.mitigation_detail` contains the expected manual-action message where relevant

## Validated

- [x] All 62 unit tests pass (`62 passed in 5.98s`)
- [x] No changes to TSG routing logic — Branch A/B/C/D/E selection unchanged
- [x] Supplementary "now" verbose search does not affect routing decisions
- [x] `alert_timestamp` parsing handles ISO 8601 with and without timezone, falls back gracefully on parse failure
- [x] Backend run `232b307d` confirmed the time window mismatch (XDS anchor was 10:28–10:32 while alerts were at 07:36–08:11)
- [x] MCP-based XDS investigation confirmed `dunghnsfailoversrc1` has 0 logs at any window, while `bqhxscndsm10pe11cx` has active XACServer verbose right now (10 rows showing `FinalizeFailover` processing)

## Pending / Open Questions

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | Backend validation run | High | Publish templates, submit a dry-run against 786460728, verify the alert-anchored window and now-verbose fallback produce signal. |
| 2 | PreProd environment mapping for `get_account` | High | Still open from predecessor change note. `dunghnsfailoversrc1` (`State_Unknown`, `AccountType=None`) resolves to `MS-BY3PrdStev52A` but has 0 XDS signal at all windows. Proper fix is backend `xstore` image upgrade. |
| 3 | Candidate sampling breadth | Medium | The stuck-pattern filter narrowed 41 → 7 → 1 account, picking a ghost PreProd account. Consider sampling across patterns or enriching metadata before sampling. Not addressed in this change — user decided different stuck patterns should track via separate incidents. |

## Assets

### XDS Investigation Evidence (2026-04-29)

- [Full investigation report](../../.copilot/../../../Users/zhdon/.copilot/session-state/c64322cf-c1bf-4640-8cc6-c92a6d59bc78/files/xds-investigation-report-786460728.md) (session artifact)

### Backend job submissions

| Date (UTC) | Job ID | dry_run | Incident | Package | Outcome | Report |
|------------|--------|---------|----------|---------|---------|--------|
| 2026-04-29 03:16 | `149f51dd-46bf-441e-8d9d-8568e53b2e79` | True | 786460728 | n/a (temp run via published template) | Submitted | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=149f51dd-46bf-441e-8d9d-8568e53b2e79_temp_run.html) |
| 2026-04-29 03:29 | `232b307d-6a27-4a83-9ef7-dbcf23193b51` | False | 786460728 | n/a (published template via `submit_template_job`) | **Fail** — `ManualActionRequired` unhandled (pre-fix) | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=232b307d-6a27-4a83-9ef7-dbcf23193b51_/Xstore/zerotoil/tsgs/failover_pending_transaction.ipynb.html) |
| 2026-04-29 07:57 | `1bb71951-418c-459e-adb6-9a512e904c52` | n/a (XDS probe) | 786460728 | `0.0.1.dev260429075710` | XDS search across alert/incident/now windows for both accounts | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=1bb71951-418c-459e-adb6-9a512e904c52_temp_run.html) |
| 2026-04-29 08:36 | `a7672f1c-4b09-4789-85ce-703618eb8f47` | True | 786460728 | `0.0.1.dev260429083632` | Dry-run with alert-anchored XDS + now-verbose + graceful ManualActionRequired + PreProd DGrep env fix | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=a7672f1c-4b09-4789-85ce-703618eb8f47_temp_run.html) |
| 2026-04-29 09:20 | `b4c162d8-2b45-40b8-a01c-a83f4c2c18be` | n/a (DGrep probe) | 786460728 | `0.0.1.dev260429083632` | DGrep endpoint probe: Test vs Production × 3 events × multiple windows, account-scoped + unscoped | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=b4c162d8-2b45-40b8-a01c-a83f4c2c18be_temp_run.html) |
