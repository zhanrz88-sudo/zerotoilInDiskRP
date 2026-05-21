---
name: tsg-end-to-end-automation
description: "End-to-end pipeline for converting a TSG wiki page into executable zero-toil Python code with full test coverage. Covers fetching TSG source from ADO repos, markdown decomposition, coding ability gap analysis, code generation, unit testing, and skill/ability documentation. USE FOR: automate TSG, TSG to code, TSG pipeline, convert TSG to zerotoil, new TSG automation, full TSG workflow."
---

# TSG End-to-End Automation Pipeline

This skill describes the full pipeline for converting a Troubleshooting Guide (TSG) from an Azure DevOps wiki/repo page into executable Python code under `zerotoil/tsgs/`, with proper test coverage and documented coding abilities.

## When to apply this skill

- A TSG exists as a wiki page or markdown file in an ADO repo (e.g., `Storage-XStore-Docs`) and you want to automate it.
- An existing automated TSG needs to be updated because the source TSG has changed.
- You need to create the full chain: markdown decomposition → coding abilities → Python code → unit tests.

## Inputs

1. **TSG source URL or repo path** (required) — e.g., an ADO wiki URL or a repo file path.
2. **TSG family ID** (required) — the kebab-case identifier used under `tsgs/<family-id>/`.
3. **Scope** (optional) — "full" (all phases) or a specific phase to run in isolation.

## Pipeline Overview (5 Phases)

```
Phase 1: Fetch & Decompose TSG    → tsgs/<family-id>/*.md
Phase 2: Coding Ability Gap Analysis → coding-abilities/*/
Phase 3: Generate/Update TSG Code  → zerotoil/tsgs/<family>.py
Phase 4: Unit Tests                → tests/tsgs/test_<family>.py
Phase 5: Verify & Document         → skill updates, ability updates
```

## Phase 1 — Fetch TSG Source & Markdown Decomposition

### Fetching from ADO Repos

TSG source pages are typically in private ADO repos requiring authentication. **Do not use web_fetch** — it won't have auth tokens.

**Correct approach**: Use the ADO MCP `repo_file` tool:
```
ado-mcp-msazure-org-repo_file:
  action: get_content
  project: One
  repositoryId: Storage-XStore-Docs    # or the target repo name
  path: /Table_Layer/tsgs/Geo/[MyTSG] Title.md
```

For wiki pages, use `ado-mcp-msazure-org-wiki` with `get_page` action instead.

### TSG Markdown Decomposition

Delegate to the **tsg-document-writer** agent. Provide it with:
- The full TSG source text
- The target folder path under `tsgs/<family-id>/`
- Any existing decomposition files (so it can update rather than overwrite)

The agent produces:
- `<family-id>.md` — main TSG overview with metadata, known-issue matrix, automation notes
- `steps/step-N-<name>.md` — one file per TSG step with detailed analysis
- `_references.md` — shared constants, log sources, error patterns, escalation contacts

**Key metadata in each step file:**
```markdown
CODING_ABILITY_DEPENDENCY: <coding-ability-id> (<specific API methods>)
AUTOMATABLE: Yes | Partially | No
```

### Validation: Read the existing decomposition files

Before updating, always read ALL existing files in the TSG folder to understand current state. This prevents accidentally losing information.

## Phase 2 — Coding Ability Gap Analysis

Invoke the `learn-coding-ability-required-by-tsgs` skill (see that skill for full methodology). Key steps:

1. **Read existing abilities first (mandatory).** Run `Get-ChildItem coding-abilities -Directory` and read every `ABILITY.md` whose name even loosely relates to the APIs in the TSG. This is the #1 source of "gotchas" and forbidden patterns and prevents reinventing wrong fallbacks.
   - Example real bug from skipping this: a fallback that passed an SRP/RSRP tenant to `xds.search_log(...)`. Both `storage-account-tenant-metadata` and `xds-log-search` clearly state RSRP is a control-plane stamp with no XDS endpoint — the call returned HTTP 500 / `EndpointNotFoundException`. Reading the abilities first would have prevented the bad code, the wasted backend run, and the misleading change-note.
2. **Inventory gaps**: For each step file, identify tools/APIs referenced but not covered by existing coding abilities.
3. **Discover APIs**: Search `.venv/Lib/site-packages/` for Python SDK implementations and `jupyter-templates/` for real usage patterns.
4. **Compare backend vs local versions** for any API that can ship in two places (e.g., `xstore.get_account` differs between the XJupyterLite image and the local `.venv`). When in doubt, submit a tiny introspection notebook (`inspect.getsource(api)`) via the `run-zerotoil-job-in-backend` skill and diff the output. Document the divergence in the relevant ability.
5. **Create/update abilities**: Under `coding-abilities/<ability-id>/`. If you discover a new constraint, update the ability *before* writing TSG code that depends on it.

### XDS API Discovery Pattern (Critical for XStore TSGs)

Many TSGs reference PowerShell cmdlets (e.g., `Get-XdsPartition`). The mapping to Python is:

1. **Find the cmdlet source**: Fetch from `Storage-XStore` repo (use `ado-mcp-msazure-org-repo_file` with `action: get_content`, `project: One`, `repositoryId: Storage-XStore`):
   - [`src/XTable/Tools/XDiagCmdLet/XdsXtable.cs`](https://msazure.visualstudio.com/One/_git/Storage-XStore?path=/src/XTable/Tools/XDiagCmdLet/XdsXtable.cs&version=GBmain) — XTable PowerShell cmdlets
   - [`src/XDiagnostics/Api/Controllers/XTable/Lib/XTableController.cs`](https://msazure.visualstudio.com/One/_git/Storage-XStore?path=/src/XDiagnostics/Api/Controllers/XTable/Lib/XTableController.cs&version=GBmain) — XDS REST API controller routes

2. **Map cmdlet → Python API**: The `xds_client` package in `.venv` mirrors the XDS REST API:
   - `Get-XdsPartition` → `XTableApi.x_table_get_partitions_stats()`
   - `Get-XdsLog` → `xds.search_log()` (via `xstore` package)
   - `Get-XdsRoleInstance` → `RoleInstancesApi.get_role_instances()`

3. **Verify with live API** via XInvestigator MCP:
   ```python
   # Use xinvestigator-mcp-run_python_code for verification
   # Important: nest_asyncio + run_until_complete pattern required
   import nest_asyncio
   nest_asyncio.apply()
   import asyncio
   from xds_client import XTableApi, ApiClient
   async def main():
       client = ApiClient()
       await client.connect_tenant("MS-SYD24PrdStr02A")
       api = XTableApi(client)
       result = await api.x_table_get_partitions_stats(...)
       return result
   code_output = asyncio.get_event_loop().run_until_complete(main())
   ```

4. **Escalation ladder** (user's explicit instruction for automation):
   1. XDS API client (Python SDK) — try first, always
   2. Geneva Actions (`xportal.acis`) — invoke cmdlet remotely
   3. Kusto — alternative data source (often has periodic snapshots)
   4. Human fallback — but ALWAYS provide full command + parameters + any partial evidence

### Key Discoveries from FailoverPendingTransaction Work

- **`x_table_get_partitions_stats()`** returns 518 columns per partition including `GeoReplayerState` (numeric), `StateMachineState` (text), `MetadataStreamName`, `LowKey`/`HighKey`
- **GeoReplayerState codes**: 101=StopReplay, 102=LiveReplay, 103=LiveReplayPause, 104=FlushReplay, 105=FlushReplayDone, 106=MigrationReplayDone
- **Pagination**: Check `result.continuation_key` — if not None, increment `page_number` and fetch next
- **Account filtering**: Client-side — check account name in `LowKey` column (the API returns all partitions on the tenant)
- **XFiles partition filtering**: Check `MetadataStreamName` contains `"xfiles!"`
- **Kusto fallback**: `GeoReplayerBlockedPartitions2` table on `xstore.kusto.windows.net/xstore`

## Phase 3 — Generate/Update TSG Code

### For New TSGs

Delegate to the **tsg-code-writer** agent. Provide:
- All markdown decomposition files (main + steps + references)
- Coding ability documents for all dependencies
- The TsgBase framework pattern (from `zerotoil.core.framework`)

### For Existing TSG Updates

When updating, first understand the existing code structure:
- Read the full Python file
- Identify which methods map to which TSG steps
- Identify routing logic (the step that branches based on incident state)

Then make surgical updates:
- Add new branches as new methods
- Update routing logic (e.g., stage tuple matching)
- Remove deprecated branches (but keep default escalation as catch-all)
- Thread new state through intermediate state management methods

### Architecture Patterns

**Routing on state tuples** (preferred for failover TSGs):
```python
p = self.primary_stage.strip().lower()
s = self.secondary_stage.strip().lower()

if (p == "preparefailover" and s == "notstarted") or \
   (p == "notstarted" and s == "preparefailover"):
    await self._branch_a(tsg_input)
elif p == "finalizefailover" and s == "finalizefailover":
    await self._branch_c(tsg_input)
else:
    await self._branch_default(tsg_input)
```

**Escalation ladder pattern** (for operations that may fail):
```python
async def _branch_with_ladder(self, tsg_input):
    # Try API first
    result = await self._try_api(tenant)
    if result is not None:
        # API succeeded — act on result
        ...
        return

    # API failed — try Kusto
    result = await self._try_kusto(tenant)
    if result is not None:
        ...
        return

    # Both failed — human fallback with FULL command
    await self._human_fallback(tsg_input, tenant)
```

**State threading** (when per-candidate state must not leak):
```python
def _set_active_candidate(self, account_name):
    self.primary_stage = ""
    self.secondary_stage = ""
    # ... reset all per-candidate fields

def _record_active_candidate_result(self):
    return {"primary_stage": self.primary_stage, ...}

def _apply_primary_summary_result(self, record):
    self.primary_stage = record.get("primary_stage", "")
```

### Approval Gates

Mutating actions (ICM transfer, incident update) must have approval gates:
```python
print("=" * 60)
print(f"APPROVAL REQUIRED: Transfer incident to {team}")
print("=" * 60)
await incident.transfer(...)
```

## Phase 4 — Unit Tests

Invoke the `zero-toil-unit-test` skill, or write tests directly. Key patterns:

### Test Structure

```python
@patch("zerotoil.tsgs.<module>.get_account")
@patch("zerotoil.tsgs.<module>.icm")
@patch("zerotoil.tsgs.<module>.xds")
@patch("zerotoil.tsgs.<module>.dgrep")
async def test_branch_x_scenario(self, mock_dgrep, mock_xds, mock_icm, mock_get_account):
    # 1. Setup DGrep mocks for step 1-3 (routing to correct branch)
    # 2. Setup XDS/Kusto mocks for step 4 (branch-specific logic)
    # 3. Setup ICM mock for step 5 (evidence posting)
    # 4. Run TSG and assert outcomes
```

### Mock Helpers

- `_make_dgrep_result(df)` — wraps DataFrame in mock with `.to_df()` and `.get_dgrep_link()`
- `_make_xds_result(df)` — wraps DataFrame in mock with `.to_df()`
- `_make_account_entity(tenant, geo_pair)` — mock account with `.TenantName`, `.GeoPairName`
- `_make_dgrep_query_side_effect(step1_df, step2_df, step3_df)` — returns different results per DGrep call

### Test Coverage Requirements

For each branch:
1. **Happy path**: Pattern found → correct action taken (transfer/escalate)
2. **Pattern not found**: Falls to default escalation
3. **Empty data**: No log entries → graceful fallback
4. **Tenant routing**: Verify which tenant is searched (Primary vs Secondary vs geo-pair)

For escalation ladder branches:
5. **API success path**: API finds data → correct action
6. **API fails, Kusto succeeds**: Fallback to Kusto → correct action
7. **Both fail**: Human fallback with full command in error message

### Running Tests

```powershell
cd zero-toil
& .venv\Scripts\Activate.ps1
python -m pytest tests/tsgs/test_<family>.py -v --tb=short
```

## Phase 5 — Verify & Document

### Verify with Live API (Optional but Recommended)

Use `xinvestigator-mcp-run_python_code` to test XDS API calls against real tenants:
- Verify column names and data formats match your parsing logic
- Confirm pagination behavior
- Check that filtering logic (account name in LowKey, table name in MetadataStreamName) works

**Critical**: The XInvestigator MCP code executor runs in an already-running event loop. Use:
```python
import nest_asyncio
nest_asyncio.apply()
code_output = asyncio.get_event_loop().run_until_complete(main())
```

Local `.venv` only has `xportal-aad` for DGrep/MDM. For XDS APIs, use XInvestigator MCP.

## Phase 6 — Real Incident Investigation & Gap Fixing

**This phase is essential.** Code generated from TSG documentation alone will have blind spots that only surface when tested against real incidents.

### Methodology

1. **Gather sample incidents** — at least 5-7 covering different stuck stages, tenants, and statuses (Active + Mitigated).
2. **Run DGrep queries manually** against real tenants to verify each Step's data source exists.
3. **Resolve accounts** via `get_account()` to verify storage tenant → geo-pair mapping.
4. **Search XDS logs** on resolved tenants (not RSRP names) to verify Step 4 diagnostic data exists.
5. **Document gaps** — which Steps return 0 rows? Which branches are unreachable?
6. **Run a dry-run backend job** before enabling writes. Instantiate the TSG with `dry_run=True` so real DGrep/XDS reads execute but ICM writes/transfers/mitigations are printed instead of performed.

### Critical Findings Pattern: RSRP Tenants

FailoverPendingTransaction incidents always come from **RSRP tenants** (Regional SRP stamps like RSRPWestUS, RSRPPublicPreprodEastUS2). Key gotchas:

- **`AccountFailoverStatisticsEvent` never exists for RSRP tenants** — Step 3 always gets 0 rows. Must have fallback.
- **`AccountFailoverEvent` also absent** — Step 2 completion check always says "not completed".
- **RSRP tenant names ≠ storage tenant names** — `get_account()` resolves to real tenants (e.g., `MS-BY3PrdStev52A`).
- **DGrep queries with `scope_conditions={"Tenant": "RSRPxxx"}` work** for RegionalSRP namespace events.
- **XDS log searches need the resolved storage tenant**, not the RSRP name.

### Fallback Chain Pattern

When a DGrep data source doesn't exist for certain tenant types, implement a fallback chain:

```
1. Primary source (DGrep event) → full data available
2. Fallback 1: Step 1 alert data (matched_stuck field) → partial data (one side only)
3. Fallback 2: Incident title parsing → minimal data
4. Unknown → generic escalation with evidence gathered so far
```

Always track the data source (`stage_source` field) so operators know the confidence level.

### DGrep Retry and Pacing Pattern

Backend runs can hit DGrep's per-client outstanding-query quota (`Reached maximum number of outstanding queries from this client (200)`). Generated TSG code should:

- Use `dgrep_query_with_retry()` from `zerotoil.core.framework` for every DGrep call.
- Keep query windows small and chunk large time ranges.
- Add light pacing between repeated chunked DGrep searches.
- Patch `asyncio.sleep` in unit tests so retry/pacing code remains fast and fully mocked.

### Dry-Run Safety Pattern

TSGs that may be tested against real incidents should accept `dry_run=True` via `TsgBase` and guard all mutating operations:

- Continue read operations: ICM fetch, DGrep, XDS, Kusto, account metadata.
- Skip writes: `add_description`, `transfer`, `mitigate`.
- Print the exact evidence/action that would have been written.
- Prefer continuing exploratory dry-run paths instead of raising manual-action exceptions that stop the report early.

### Single-Side Routing Pattern

When fallback provides only one side's stage (e.g., "SecondaryStuck.PrepareFailover"):

- Route to the branch for the known stage
- For tenant-specific searches (Branch A), search **both** primary and geo-pair tenants
- Include `stage_source` in evidence so operators know this is partial information
- Do NOT assume the other side's state — leave it as unknown

### Change Notes

After fixing gaps, document changes in `docs/change-notes/` following the template. Include:
- Before/after comparison per incident showing routing differences
- Account resolution results and XDS log search outcomes
- Quantified improvement (% of incidents reaching specialized branches)


### For End-to-End TSG Runs

Use the `run-zerotoil-job-in-backend` skill to submit the TSG to the XJupyterLite backend.

### Update Coding Abilities

After discovering new API patterns:
1. Update `ABILITY.md` with new methods/endpoints
2. Add reference examples with validation levels (✅ Validated, 🔶 API source, ⚠️ Docs-only)
3. Update `coding-abilities/README.md` index

### Update TSG References

Update `_references.md` with:
- New error patterns and log sources discovered
- Escalation contacts verified during investigation
- State codes and their meanings (e.g., GeoReplayerState codes)

## MCP Access Patterns Reference

| Data Source | MCP Tool | Notes |
|---|---|---|
| ADO repo files | `ado-mcp-msazure-org-repo_file` | `project=One`, action=`get_content` |
| ADO wiki pages | `ado-mcp-msazure-org-wiki` | action=`get_page` |
| XDS API (live) | `xinvestigator-mcp-run_python_code` | nest_asyncio pattern required |
| DGrep queries | `xinvestigator-mcp-run_d_grep_events_query` | Or via xportal-aad in local .venv |
| Kusto queries | `xinvestigator-mcp-query_kusto` | Or via xportal.kusto in code |
| ICM incidents | `icm-mcp-prod-get_incident_details_by_id` | For checking real incident data |
| Code search | `ado-mcp-msazure-org-search_code` | Search across repos |

## Agent Delegation Reference

| Task | Agent/Skill | Mode |
|---|---|---|
| TSG markdown decomposition | `tsg-document-writer` agent | background |
| TSG code generation (new) | `tsg-code-writer` agent | background |
| Coding ability gap analysis | `learn-coding-ability-required-by-tsgs` skill | inline |
| API discovery | `learn-xds-api-coding-ability` skill | inline |
| Unit test writing | `zero-toil-unit-test` skill | inline |
| Plan validation | `rubber-duck` agent | sync |
| Backend job submission | `run-zerotoil-job-in-backend` skill | inline |

## Worked Example: FailoverPendingTransaction TSG

### Source
ADO path: `Storage-XStore-Docs` repo → `/Table_Layer/tsgs/Geo/[FailoverPendingTransaction]...md`

### Pipeline Execution

**Phase 1**: Fetched via `ado-mcp-msazure-org-repo_file`. Launched `tsg-document-writer` (background) → updated 4 markdown files with 5 branches (A-E), DnsSwitch stage, new escalation contacts.

**Phase 2**: Invoked `learn-coding-ability-required-by-tsgs`. Key discovery: `Get-XdsPartition` maps to `XTableApi.x_table_get_partitions_stats()`. Verified GeoReplayerState is a numeric column (not text parsing). Updated `xds-api-call` coding ability.

**Phase 3**: Updated `failover_pending_transaction.py`:
- Added `DnsSwitch` to `_STAGE_ORDER`
- Rewrote routing from string-based to (primary, secondary) tuple-based
- Refined Branch A (directional routing to NotStarted side)
- New Branch B (both PrepareFailover → GeoConfigOff on Primary)
- New Branch C (FinalizeFailover → XDS API → Kusto → human ladder)
- New Branch D (DnsSwitch → 0x830a382d on Secondary)
- Renamed old default to Branch E

**Phase 4**: Rewrote test classes:
- `TestBranchBBothPrepareFailover`: 4 tests (GeoConfigOff found/not, empty log, Primary tenant)
- `TestBranchCFinalizeFailover`: 4 tests (API success, API no match, API fail+Kusto, both fail)
- `TestBranchDDnsSwitch`: 3 tests (error found, not found, Secondary tenant)
- Fixed pre-existing `test_prepare_failover_llam_split_block` stage data
- All 44 tests pass.

**Phase 5**: Updated coding abilities, TSG references, and wrote this skill document.

**Phase 6**: Investigated real incidents and fixed gaps discovered from live data:
- RSRP tenants do not emit `AccountFailoverStatisticsEvent` / `AccountFailoverEvent`.
- Added fallback from Step 1 alert `matched_stuck` and incident title.
- Added single-side routing and finalize-stage coverage.

**Phase 7**: Added DGrep retry resilience and safe dry-run mode:
- `dgrep_query_with_retry()` for DGrep throttling.
- `FailoverPendingTransaction(dry_run=True)` skips ICM writes while keeping reads active.
- Unit tests verify dry-run skips `add_description`, `transfer`, and `mitigate`.

## Validation Checklist

Before considering the pipeline complete:

- [ ] All TSG markdown files updated with correct `CODING_ABILITY_DEPENDENCY` and `AUTOMATABLE` assessments
- [ ] All referenced APIs validated (✅/🔶/⚠️ level documented)
- [ ] Python file passes `ast.parse()` (syntax check)
- [ ] All unit tests pass (`pytest -v`)
- [ ] Each branch has tests for: happy path, pattern not found, empty data, tenant routing
- [ ] Escalation ladder branches have tests for: API success, API fail → Kusto, both fail → human
- [ ] Human fallback messages include full command + parameters (never bare escalation)
- [ ] DGrep calls use `dgrep_query_with_retry()` and chunked searches are paced
- [ ] Dry-run mode guards every write path before backend validation against real incidents
- [ ] Coding abilities updated with new discoveries
- [ ] TSG `_references.md` updated with new patterns and contacts
