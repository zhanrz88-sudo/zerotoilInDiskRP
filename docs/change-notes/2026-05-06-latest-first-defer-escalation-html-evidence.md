# Change Note: Latest-First Sampling, Defer Escalation, Both-NotStarted Routing, Timezone-Aware Escalation, HTML Evidence

**Date:** 2026-05-06
**Author:** zhdon (with Copilot)
**Commit(s):** Pending
**TSG / Component:** `zerotoil/tsgs/failover_pending_transaction.py`, `tests/tsgs/test_failover_pending_transaction.py`
**Predecessor:** [2026-04-29 XDS anchor / now-verbose / graceful manual](2026-04-29-xds-anchor-now-verbose-graceful-manual.md)

---

## Why (Motivation)

- **Root cause / trigger:** Backend run `36495e9e-469f-477c-af94-3e08416918a1` against incident `791887914` exposed five gaps:
  1. **Stale candidate first.** Step 1 dedup kept the latest `alert_timestamp` per `(operation_id, account_name)` but did **not** sort the deduped list before truncating to `_MAX_SAMPLED_ACCOUNTS`. With 2 candidates surfaced, the freshest log message could be ranked second.
  2. **`StartTimeInUtc` ignored.** Two candidates from the same alert timestamp tied — the candidate whose underlying failover was started more recently (likelier to be actionable) was not preferred.
  3. **Loop gave up after one candidate.** The candidate loop broke as soon as `mitigation_status in {"Transferred","Escalated"}`. For the incident above, the first candidate's stuck-pattern hit `_branch_e_default_escalation` → `_escalate_ra_ximi` raised `ManualActionRequired`, the loop broke, and the second candidate was never investigated.
  4. **Both-NotStarted skipped Branch A.** When Step 3 reported `Primary=NotStarted, Secondary=NotStarted` (common on RSRP tenants where the failover never visibly progresses), Step 4 fell straight to default escalation — even though Branch A's XACServer Verbose + TableMaster Error searches on both tenants would have produced useful triage evidence.
  5. **Escalation route hard-coded to ximi.** The source TSG specifies *RA XGeo DRI in ICM* during Redmond working hours and `ximi@microsoft.com` during China working hours; the implementation always used ximi.
  6. **ICM evidence was unreadable plain text.** `incident.add_description` posted a plain `\n`-joined block with no tables and no actual log rows — the on-call had to click every link to see what we found.
- **Impact if not fixed:** Slower, less-correct triage; missed evidence on shared-load alerts; on-call pages routed to the wrong on-shift team; reviewers had to open every DGrep/XDS link to inspect findings.
- **Related incidents:** `791887914`.

## Where (Files Changed)

| File | Type | Summary |
|------|------|---------|
| `zerotoil/tsgs/failover_pending_transaction.py` | Modified | (1) Parse `StartTimeInUtc` + sort candidates latest-first; (2) defer escalations until all sampled accounts are tried; (3) both-NotStarted routes to Branch A and Branch A searches both tenants; (4) timezone-aware escalation target via `_select_escalation_target`; (5) HTML evidence summary with `_record_log_sample` + `_build_evidence_summary_html`, posted with `is_html=True` |
| `tests/tsgs/test_failover_pending_transaction.py` | Modified | Existing assertions made route-agnostic (`ximi OR XGeo DRI`); added 3 unit tests for `_select_escalation_target`; updated Step 5 evidence assertion for HTML format |
| `jupyter-templates/Xstore/zerotoil/tsgs/failover_pending_transaction.ipynb` | Modified | Republished from updated `.py` |

## What (Major Logic)

### Change 1: Latest-first sampling (alert timestamp + StartTimeInUtc)

Step 1 now:

- Parses the operation `StartTimeInUtc:` substring from the failover alert message into a per-candidate `start_time_in_utc_raw` field.
- After deduplicating by `(operation_id, account_name)`, sorts the candidate list with key `(alert_timestamp DESC, start_time_in_utc DESC)` **before** truncating to `_MAX_SAMPLED_ACCOUNTS`.
- The "Sampled candidate accounts" log line now prints `alert_ts=<...>` and `start_time=<...>` per candidate so the ordering is visible in reports.

Why: the freshest log message is the strongest XDS-anchor signal; among same-alert-timestamp ties, a more recently started failover is the likelier actionable one.

### Change 2: Defer escalation until all sampled accounts are exhausted

- Added `self._defer_escalation: bool` and `self._deferred_escalations: list[dict]`.
- During the per-candidate loop in `_run`, `_escalate_ra_ximi` only **records** the escalation intent (status `EscalationDeferred`, no ICM write, no raise) when `_defer_escalation` is True.
- The loop now only breaks early on a real action (`Transferred`) or `is_completed=True`. An `EscalationDeferred` outcome continues to the next sampled account.
- After the loop, `_perform_deferred_escalation` runs **once** with combined evidence + reasons from every sampled candidate, then performs the actual ICM `add_description` and raises `ManualActionRequired`.
- Per-candidate summaries are retroactively promoted from `EscalationDeferred` → `Escalated` so the final TSG output reflects the action that was actually taken.

### Change 3: Both-NotStarted routes to Branch A (both tenants)

- `_step_4_mitigate_or_escalate` adds an explicit branch for `p == "notstarted" and s == "notstarted"` that routes to `_branch_a_prepare_failover` to capture XDS evidence before the deferred escalation fires.
- `_branch_a_prepare_failover` now special-cases the both-NotStarted shape and searches **both** the home tenant and the geo-pair tenant (previously only the side flagged as NotStarted was searched).
- Routing decision is unchanged — none of the existing TableMaster split-failure regexes hit the "wait split" payload seen in incident 791887914 — but the evidence now lands in the escalation summary.

### Change 4: Timezone-aware escalation routing

- New static helper `_select_escalation_target(now=None)` returns `(target_label, route_description, action_keyword)`:
  - **China working hours** (Asia/Shanghai weekday, 09:00 ≤ hour < 18:00) → `ximi@microsoft.com`.
  - **Otherwise** → *RA XGeo DRI in ICM* (Redmond on-call covers everything else).
- `_escalate_ra_ximi` calls the helper at the moment of the actual escalation (deferred or not) and uses its outputs in `mitigation_detail`, the ICM HTML body, the `MANUAL ACTION REQUIRED` print block, and the `ManualActionRequired` message.
- 3 new unit tests cover China business hours, China after-hours, and weekend.
- Existing assertions that pinned `"ximi@microsoft.com"` were relaxed to `("ximi@microsoft.com" in detail) or ("XGeo DRI" in detail)` so they remain stable in any timezone.

### Change 5: HTML evidence summary with sample logs

- Added `self.evidence_log_samples: list[dict]` plus `_record_log_sample(label, link, df, max_rows=5, message_max=400)` that captures up to 5 rows per query as `df.to_html()` (with the `message` column truncated for readability).
- The recorder is wired into the major queries:
  - Step 1 — DGrep `ServiceBackgroundActivityEvent` (PendingFailover alerts).
  - Step 2 — DGrep `AccountFailoverEvent`.
  - Step 3 — DGrep `AccountFailoverStatisticsEvent`.
  - Branch A — XACServer Verbose and TableMaster Error per searched tenant.
- New `_build_evidence_summary_html(tsg_input, extra_links=None, extra_html="")` renders:
  - A meta `<table>` with incident / tenant / account / stage / mitigation fields.
  - A `<ul>` of evidence links.
  - A "Per-account investigation" `<table>` for sampled candidates.
  - A "Sample logs" section: `<h4>label (showing N of M rows) — link</h4>` + the captured `<table>` per query.
  - An optional caller-supplied `extra_html` block for action / reason / manual instructions.
- All four `incident.add_description(...)` call sites — `_transfer_incident`, `_escalate_ra_ximi`, `_branch_c_human_fallback`, `_step_5_update_incident` — now post the HTML body with `is_html=True`. Plain-text dry-run preview is kept unchanged for terminal readability.

## Validated

- [x] Unit tests pass: **65 passing** (62 existing + 3 new for `_select_escalation_target`); 1 existing assertion updated for HTML body.
- [x] Backend dry-run against incident `791887914` confirms (a) both candidates investigated with the new ordering, (b) deferred escalation aggregates evidence, (c) both-NotStarted now triggers Branch A's both-tenant search (50 / 100-row hits on the secondary tenant for `stnviumpbmsqa` proved the search path).
- [ ] Backend run against an incident *with* a known-pattern hit (e.g. LLAM split block) — pending.
- [ ] Live (non-dry-run) run after PR review.

## Pending / Open Questions

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | Confirm the exact RA XGeo DRI route inside ICM (team / on-call queue name) so the manual action message can be more specific than "RA XGeo DRI in ICM". | Med | Helper currently emits the generic label `"XGeo DRI (RA in ICM)"`. |
| 2 | Decide whether to add a new "wait split" pattern to Branch A. Per user direction (2026-05-06), this is **NOT** being added; both-NotStarted with no known pattern continues to escalate with full evidence. | Closed | Documented for completeness. |
| 3 | `_record_log_sample` fixes `message_max` at 400 chars; consider per-source overrides if a future signal is buried beyond that cutoff. | Low | Search link is always included so the on-call can see the full message. |

## Assets

### Backend job submissions

| Date (UTC) | Job ID | dry_run | Incident | Package | Outcome | Report |
|------------|--------|---------|----------|---------|---------|--------|
| 2026-05-06 03:20 | `762eb035-cbcb-4669-a8b1-0e9226a14367` | True | `791887914` | `0.0.1.dev260506032006` | Success — both candidates investigated, latest-first ordering and deferred escalation verified | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=762eb035-cbcb-4669-a8b1-0e9226a14367_temp_run.html) |
| 2026-05-06 03:35 | `4be384a1-fcfc-49e2-b1d0-eaf7c6e41a85` | True | `791887914` (XDS-only test) | `0.0.1.dev260506032006` | Success — confirmed secondary tenant `MS-SJC23PrdStr04B` returns 50 XAC verbose / 100 TM error rows for `stnviumpbmsqa` ("wait split", not LLAM) | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=4be384a1-fcfc-49e2-b1d0-eaf7c6e41a85_temp_run.html) |
| 2026-05-06 04:15 | `80af6459-f7f5-442a-b274-f7b53f51da6d` | True | `791887914` | `0.0.1.dev260506041544` | Success — both-NotStarted now flows through Branch A; timezone-aware escalation target chosen at runtime | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=80af6459-f7f5-442a-b274-f7b53f51da6d_temp_run.html) |
| 2026-05-06 05:10 | `b4b7ac10-1e11-4269-9bff-4303daeddb3a` | True | `791887914` | `0.0.1.dev260506051009` | Success — HTML evidence summary with sample log tables verified in dry-run preview | [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=b4b7ac10-1e11-4269-9bff-4303daeddb3a_temp_run.html) |
