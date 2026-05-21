# Change Note: Critical Gap Fixes from Real Incident Investigation

**Date:** 2026-04-28
**Author:** zhdon (with Copilot)
**Commit(s):** `3f05e6e66d` (TSG rewrite), `10e33188ec` (gap fixes)
**TSG / Component:** `zerotoil/tsgs/failover_pending_transaction.py`

---

## Why (Motivation)

- **Root cause / trigger:** Investigated 7 real FailoverPendingTransaction incidents to validate the TSG automation code. Found that **Branches A–D were unreachable** for ALL real incidents because `AccountFailoverStatisticsEvent` (Step 3's DGrep data source) **never exists for RSRP tenants**. All FailoverPendingTransaction incidents originate from RSRP tenants (RSRPWestUS, RSRPPublicPreprodEastUS2, etc.), so Step 3 always produced "Unknown" stage → Step 4 always fell to Branch E (generic escalation).
- **Impact if not fixed:** The TSG automation was essentially a no-op beyond Step 1 alert parsing — every incident would get generic "escalate to RA/ximi" without any XDS log investigation or pattern matching. Operators got no actionable information.
- **Related incidents:**
  - 786460728 — SecondaryStuck.PrepareFailover in RSRPPublicPreprodEastUS2 (Active)
  - 786460717 — SecondaryStuck.SoftFinalizeFailover in RSRPPublicPreprodEastUS2 (Active)
  - 785335929 — SecondaryStuck.SoftFinalizeFailover in RSRPPublicPreprodEastUS2 (Active)
  - 784904838 — SecondaryStuck.PrepareFailover in RSRPWestUS (Mitigated)
  - 784435565 — SecondaryStuck.HardFinalizeFailover in RSRPWestUS2 (Mitigated)
  - 784423331 — SecondaryStuck.HardFinalizeFailover in RSRPWestUS2 (Mitigated)
  - 783931952 — SecondaryStuck.HardFinalizeFailover in RSRPWestUS2 (Mitigated)

## Where (Files Changed)

### Commit 1: `3f05e6e66d` — TSG rewrite (Branches B–D, XDS API escalation)

| File | Type | Summary |
|------|------|---------|
| `zerotoil/tsgs/failover_pending_transaction.py` | Modified | Full rewrite of Branches B–E, added XDS API escalation ladder in Branch C, tuple-based routing |
| `tests/tsgs/test_failover_pending_transaction.py` | Modified | Replaced Branch B tests, added Branch C (4 tests), Branch D (3 tests) |
| `coding-abilities/xds-api-call/ABILITY.md` | Modified | Updated XTableApi partition stats methods |
| `coding-abilities/xds-api-call/references/xtable-xstream-xcompute.md` | Modified | Partition stats examples, Kusto fallback, GeoReplay state codes |
| `tsgs/.../step-4-mitigate-or-escalate.md` | Modified | Full rewrite with 5 branches |
| `tsgs/.../_references.md` | Modified | New patterns, contacts, XDS partition state section |
| `.github/skills/tsg-end-to-end-automation/SKILL.md` | Added | Full E2E pipeline skill document |

### Commit 2: `10e33188ec` — Gap fixes from incident investigation

| File | Type | Summary |
|------|------|---------|
| `zerotoil/tsgs/failover_pending_transaction.py` | Modified | Step 3 fallback chain, `_STAGE_ORDER` update, single-side routing, Branch A multi-tenant search |
| `tests/tsgs/test_failover_pending_transaction.py` | Modified | 15 new tests for fallback chain, single-side routing, stage constants |

## What (Major Logic)

### Change 1: Step 3 fallback chain (most critical)

When `AccountFailoverStatisticsEvent` returns 0 rows (which is **always** for RSRP tenants), the code now has a 3-tier fallback:

1. **`matched_stuck` from Step 1 alert data** — The DGrep `ServiceBackgroundActivityEvent` alert messages contain `"dimensionValues: SecondaryStuck.PrepareFailover"` which is parsed in Step 1 into the `matched_stuck` field. Step 3 now parses this as `(side, stage)` and sets `primary_stage` or `secondary_stage` accordingly.
2. **Incident title** — The ICM title always contains `"SecondaryStuck.PrepareFailover in RSRPWestUS"`. The `expected_stuck_location` and `expected_stuck_stage` fields from `_extract_input_from_incident()` serve as last resort.
3. **Unknown** — Only if all sources fail.

New `stage_source` field tracks provenance (`"statistics_event"`, `"matched_stuck"`, `"incident_title"`) so operators know the confidence level of the stage determination.

### Change 2: SoftFinalizeFailover and HardFinalizeFailover stages

Real incidents showed 5/7 accounts at `SoftFinalizeFailover` and others at `HardFinalizeFailover`. These are sub-phases of the FinalizeFailover step. Added to `_STAGE_ORDER`:
```
NotStarted → PrepareFailover → PollFailover → FinalizeFailover → 
SoftFinalizeFailover → HardFinalizeFailover → PollFinalizeFailover → 
DnsSwitch → ShortTermCleanup
```

New `_FINALIZE_STAGES` set (`{"finalizefailover", "softfinalizefailover", "hardfinalizefailover"}`) lets Branch C handle all three variants.

### Change 3: Single-side routing

When only one side's stage is known (from `matched_stuck`), new routing path in Step 4:
- `PrepareFailover` → Branch A (with both-tenant search)
- `SoftFinalizeFailover` / `HardFinalizeFailover` / `FinalizeFailover` → Branch C
- `DnsSwitch` → Branch D
- Other → Branch E

### Change 4: Branch A multi-tenant search

When invoked via single-side routing, Branch A now searches **both** `storage_tenant` and `geo_pair_tenant` instead of guessing which side is NotStarted. Results are combined for pattern matching. This was a rubber-duck agent recommendation — avoids missing evidence when the stuck side is ambiguous.

### Change 5: XDS API escalation ladder (Commit 1)

Branch C now uses a 3-tier escalation:
1. **XDS API** (`x_table_get_partitions_stats`) — client-side filter for XFiles partitions with `GeoReplayerState == 102` (LiveReplay)
2. **Kusto** (`GeoReplayerBlockedPartitions2` table) — backup when API fails
3. **Human DRI** — full `Get-XdsPartition` PowerShell command with parameters

### Change 6: Tuple-based routing (Commit 1)

Step 4 now routes on `(primary_stage, secondary_stage)` tuples instead of a single `effective_stage`. This enables precise handling of asymmetric stages (e.g., Primary=PrepareFailover, Secondary=NotStarted → Branch A goes to secondary's tenant).

## Validated

- [x] Unit tests pass (59 tests, 15 new in commit 2, ~10 new in commit 1)
- [x] DGrep queries verified against real RSRP tenants (RSRPPublicPreprodEastUS2, RSRPWestUS) via XInvestigator MCP
- [x] `AccountFailoverStatisticsEvent` confirmed absent for RSRP tenants (tested production + preprod)
- [x] `get_account()` resolves RSRP accounts to real storage tenants (e.g., dunghnsfailoversrc1 → MS-BY3PrdStev52A)
- [x] XDS log search works on resolved storage tenants (found 20 rows for bqhxscndsm10pe11cx on MS-DSM10PrdSte11D)
- [x] XDS API `x_table_get_partitions_stats` verified: returns 518 columns including GeoReplayerState
- [x] Rubber-duck critique applied (search both tenants, stage_source tracking, don't reuse branches unchanged)
- [x] No regressions in existing 44 tests

## Pending / Open Questions

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | Step 2 completion check also fails for RSRP | Low | `AccountFailoverEvent` returns 0 rows. Current behavior (assume not completed) is safe — investigate means we always gather evidence. False-positive completion would be worse. |
| 2 | XDS log search time window may miss data | Medium | Uses `incident_start_time ± 15min` but some failovers started months ago. Consider using DGrep alert timestamps as anchor instead. |
| 3 | Environment detection (PUBLICPREPROD vs PUBLICAZURE) | Low | DGrep `environment="Production"` works for both, but may not be correct. Incidents have `occuringLocation.environment` field that could be used. |
| 4 | Some accounts have `GeoPairName: None` | Low | Code falls back to `storage_tenant` which works, but branch routing for geo-related operations (Branch A, C) may not have the secondary stamp. |
| 5 | LLAM split block ICM team path | Medium | `target_team="StorageCRM"` in Branch A transfer — needs confirmation from team. |
| 6 | End-to-end backend run not yet tested | High | Should run via `run-zerotoil-job-in-backend` skill against a real incident to validate full flow. |

## Assets

- [Incident improvement report](assets/2026-04-28-incident-improvement-report.md) — Before/after comparison showing what new information the TSG code produces for real incidents.
