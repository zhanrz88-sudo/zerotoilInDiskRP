---
name: zero-toil-unit-test
description: "Write and run unit tests for generated TSG code under zerotoil/tsgs/. Covers mocking DGrep/ICM/Kusto APIs, testing async step methods, and verifying parsing logic with real incident data. USE FOR: unit test, write test, test TSG, mock DGrep, mock ICM, test parsing, test step method, verify TSG logic, test extraction."
---

# Zero-Toil Unit Test

This skill teaches how to write and run **unit tests** for generated TSG code in the ZeroToil framework using **pytest**.

Unit tests use **mock data only** — all external APIs (DGrep, ICM, Kusto, XDS, ACIS) are mocked so tests run entirely offline with zero external dependencies. The goal is to verify every TSG step's parsing logic, branching paths, error handling, and output construction.

## When to apply this skill

- Writing unit tests for any TSG under `zerotoil/tsgs/`.
- Verifying parsing/extraction logic against real incident or DGrep data.
- Regression-testing a fix to a TSG step method.
- Testing `_extract_input_from_incident()` with example incident titles.

## Test framework and configuration

Tests are managed by **pytest** with configuration in `pyproject.toml`.

### Key files

| File | Purpose |
|---|---|
| `pyproject.toml` | Pytest configuration: `testpaths`, `asyncio_mode`, markers, default `addopts` |
| `tests/conftest.py` | Auto-applies the `unittest` marker to any test without an explicit category marker |
| `tests/tsgs/test_<module>.py` | Test files — one per TSG module |

### Conventions

| Item | Convention |
|---|---|
| Test directory | `tests/tsgs/` |
| File naming | `test_<tsg_module>.py` (mirrors `zerotoil/tsgs/<tsg_module>.py`) |
| Test runner | `pytest` — **never** use `python -m unittest` |
| Test classes | Plain classes — **do not** inherit from `unittest.TestCase` or `unittest.IsolatedAsyncioTestCase` |
| Async tests | Plain `async def test_*` methods — pytest-asyncio with `asyncio_mode = "auto"` handles them |
| Assertions | Plain `assert` statements — **do not** use `self.assertEqual` or other unittest assert methods |
| Mocking | `unittest.mock.patch`, `AsyncMock`, `MagicMock` (stdlib mocking — this is the only `unittest` import) |
| Virtual env | `.venv` |

### Test markers (three categories)

Tests are categorized using pytest markers (defined in `pyproject.toml`):

| Marker | Scope | CI | Description |
|---|---|---|---|
| `@pytest.mark.unittest` | All APIs mocked, no external access | ✅ Default | Test parsing logic, step methods, branching, error handling with mock data |
| `@pytest.mark.integrationtest` | Mock + real data, requires API access | ❌ | Test real data access and API calls in staging; run via `run-zerotoil-job-in-backend` skill |
| `@pytest.mark.e2etest` | Full TSG against live incidents | ❌ | Complete TSG execution in real environment, some mocking for path coverage |

**How auto-marking works:** `tests/conftest.py` checks each collected test for a category marker (`unittest`, `integrationtest`, or `e2etest`). If none is present, `unittest` is auto-applied. This means:

- **Tests without any explicit marker are unit tests** — just write them, no decorator needed.
- Tests with only `@pytest.mark.asyncio` (auto-applied by `asyncio_mode = "auto"`) still get `unittest` because the auto-marker checks only for category markers, not framework markers.
- **Only mark tests explicitly** when they are `integrationtest` or `e2etest`.

### Running tests

```bash
cd zero-toil

# Run all unit tests (default — same as CI)
pytest -v

# Run tests for one TSG module
pytest tests/tsgs/test_failover_pending_transaction.py -v

# Run a specific test class
pytest tests/tsgs/test_failover_pending_transaction.py::TestStep1ExtractFailoverContext -v

# Run a single test method
pytest tests/tsgs/test_failover_pending_transaction.py::TestStep1ExtractFailoverContext::test_extracts_operation_id_and_account -v

# Run integration tests (requires API access)
pytest -m integrationtest -v

# Run everything (override default filter)
pytest -m "" -v
```

**Why `pytest -v` only runs unit tests:** `pyproject.toml` sets `addopts = "-m unittest"`. This default filter is applied when no `-m` flag is given. The CI pipeline runs the same command.

## How to write tests (async pattern)

### Critical: async tests with pytest-asyncio

TSG methods are `async`. The project uses `asyncio_mode = "auto"` in `pyproject.toml`, which means:

- **Write `async def test_*` methods directly** — pytest-asyncio detects and runs them automatically.
- **Do NOT** inherit from `unittest.IsolatedAsyncioTestCase` — that is the old stdlib approach and is incompatible with pytest's assertion introspection and plugin ecosystem.
- **Do NOT** add `@pytest.mark.asyncio` manually — `asyncio_mode = "auto"` applies it for you.
- **Use `await`** in tests just like in the TSG code.

```python
# ✅ Correct: plain class, async method, plain assert
class TestMyStep:
    async def test_parses_data(self):
        tsg = MyTsg()
        await tsg._step_1_do_something(my_input)
        assert tsg.some_field == "expected"

# ❌ Wrong: do NOT inherit from unittest.IsolatedAsyncioTestCase
class TestMyStep(unittest.IsolatedAsyncioTestCase):
    async def test_parses_data(self):
        ...
```

### Assertion style

Use plain `assert` statements. Pytest rewrites them to provide rich failure messages.

```python
# ✅ Correct pytest style
assert tsg.account_name == "ppthdprod"
assert result.is_completed
assert not result.is_completed
assert "tenant_name" in str(ctx.value)
assert "GeoConfigOff" not in tsg.xds_evidence_summary
assert len(tsg.dgrep_links) >= 1
assert mock_dgrep.query.call_count == 2

# ❌ Wrong: do NOT use self.assert* methods
self.assertEqual(tsg.account_name, "ppthdprod")
self.assertTrue(result.is_completed)
self.assertIn("tenant_name", str(ctx.exception))
```

### Exception testing

Use `pytest.raises` (not `self.assertRaises`):

```python
import pytest

async def test_raises_when_tenant_not_found(self):
    tsg = _make_tsg()
    incident = _make_incident("No tenant info here at all")
    with pytest.raises(ValueError) as ctx:
        await tsg._extract_input_from_incident("111", incident)
    assert "tenant_name" in str(ctx.value)  # note: ctx.value, not ctx.exception
```

## Hard rules

- **Use `pytest` as the test runner** — configured in `pyproject.toml`. Never use `python -m unittest`.
- **Plain classes, plain asserts** — no `unittest.TestCase` inheritance, no `self.assert*` methods.
- **Mock all external APIs** — `xportal.dgrep`, `xportal.icm`, `xportal.kusto`, `xds_client`, `xportal.acis` are not available locally. Every call must be mocked.
- **Use `AsyncMock` for async APIs** — all xportal/xds_client calls are async.
- **Use real data for mock construction** — use MCP servers, tools, and Python code execution to access real data sources (DGrep, ICM, Kusto) and capture real outputs. Convert those into mock DataFrames for tests. This catches real-world parsing bugs that synthetic data misses.
- **One test file per TSG module** — `test_<tsg_module>.py` maps to `zerotoil/tsgs/<tsg_module>.py`.
- **Reset mutable class attributes** — TSG classes use class-level list/dict defaults (e.g., `dgrep_links: list[str] = []`). Create fresh instances and override with instance attributes: `tsg.dgrep_links = []`.
- **Do not import xportal/xds_client directly** — patch them via `unittest.mock.patch` on the TSG module's namespace.
- **Mark non-unit tests explicitly** — apply `@pytest.mark.integrationtest` or `@pytest.mark.e2etest`. Unmarked tests are auto-classified as `unittest`.
- **Cover all execution paths** — test happy path, error paths, edge cases (empty results, missing columns, fallback queries), and `ManualActionRequired` branches.

## Mocking patterns

### Mock DGrep query result

DGrep returns a result object with `.to_df()` (returns a pandas DataFrame) and `.get_dgrep_link()` (returns a URL string).

```python
import pandas as pd
from unittest.mock import MagicMock

def _make_dgrep_result(df: pd.DataFrame) -> MagicMock:
    """Create a mock DGrep query result."""
    result = MagicMock()
    result.to_df.return_value = df
    result.get_dgrep_link.return_value = "https://fake-dgrep-link"
    return result
```

**Important: DGrep column name casing.** DGrep returns schema-native column names, not the names in the MQL `select` clause. For example, `select Message` → column is `message` (lowercase). The TSG code normalizes columns to lowercase after `to_df()`. Test DataFrames should use the **schema-native** casing to reproduce real behavior.

### Mock ICM incident

```python
from unittest.mock import MagicMock
from datetime import datetime

def _make_incident(title: str, create_date: datetime = None, descriptions: list = None) -> MagicMock:
    incident = MagicMock()
    incident.Title = title
    incident.Summary = ""
    incident.CreateDate = create_date or datetime(2026, 1, 1)
    incident.Descriptions = descriptions or []
    return incident
```

### Mock XDS log search result

```python
def _make_xds_result(df: pd.DataFrame) -> MagicMock:
    """Create a mock XDS log search result with .to_df()."""
    result = MagicMock()
    result.to_df.return_value = df
    return result
```

### Mock account entity

```python
def _make_account_entity(
    tenant_name: str = "MS-SYD24PrdStr02A",
    geo_pair_name: str = "MS-MEL23PrdStr11D",
    account_type: str = "GRS",
) -> MagicMock:
    entity = MagicMock()
    entity.TenantName = tenant_name
    entity.GeoPairName = geo_pair_name
    entity.AccountType = account_type
    return entity
```

### Patching external APIs in step methods

Use `@patch` on the module-level import in the TSG file. The patch target is the **TSG module's namespace**, not the original package.

```python
from unittest.mock import AsyncMock, patch

class TestMyStep:

    @patch("zerotoil.tsgs.my_tsg_module.dgrep")
    async def test_step_parses_data(self, mock_dgrep):
        df = pd.DataFrame({...})  # real or synthetic data
        mock_dgrep.query = AsyncMock(return_value=_make_dgrep_result(df))

        tsg = _make_tsg()
        await tsg._step_1_do_something(_make_input())

        assert tsg.some_field == "expected_value"
```

### Patching ICM in a step method

```python
@patch("zerotoil.tsgs.my_tsg_module.icm")
async def test_step_updates_incident(self, mock_icm):
    mock_incident = MagicMock()
    mock_incident.add_description = AsyncMock()
    mock_incident.mitigate = AsyncMock()
    mock_icm.get_incident = AsyncMock(return_value=mock_incident)

    tsg = _make_tsg()
    await tsg._step_5_update_incident(_make_input())

    mock_incident.add_description.assert_called_once()
```

### Multiple DGrep queries in one step (side_effect)

When a step calls `dgrep.query()` multiple times, use `side_effect`:

```python
mock_dgrep.query = AsyncMock(side_effect=[
    _make_dgrep_result(first_query_df),
    _make_dgrep_result(second_query_df),
])
```

### Patching multiple APIs in one test

Stack `@patch` decorators. **Order matters**: decorators are applied bottom-up, so the first method argument after `self` corresponds to the **last** `@patch`.

```python
@patch("zerotoil.tsgs.my_tsg_module.get_account")
@patch("zerotoil.tsgs.my_tsg_module.xds_search")
@patch("zerotoil.tsgs.my_tsg_module.dgrep")
async def test_end_to_end(self, mock_dgrep, mock_xds_search, mock_get_account):
    mock_get_account.return_value = _make_account_entity()
    mock_xds_search.search = AsyncMock(return_value=_make_xds_result(xds_df))
    mock_dgrep.query = AsyncMock(side_effect=[...])
    ...
```

## Test structure template

```python
"""Unit tests for <TsgName> TSG.

Run:
    cd zero-toil
    pytest tests/tsgs/test_<tsg_module>.py -v
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pandas as pd

from zerotoil.tsgs.<tsg_module> import (
    <TsgName>,
    <TsgName>Input,
    ManualActionRequired,
)


# ── Helpers ──────────────────────────────────────────────────


def _make_dgrep_result(df: pd.DataFrame) -> MagicMock:
    result = MagicMock()
    result.to_df.return_value = df
    result.get_dgrep_link.return_value = "https://fake-dgrep-link"
    return result


def _make_tsg() -> <TsgName>:
    tsg = <TsgName>()
    tsg.dgrep_links = []  # Clean instance state — avoid shared class-level list
    return tsg


def _make_input(**overrides) -> <TsgName>Input:
    defaults = dict(
        incident_id="12345",
        tenant_name="RSRPWestEurope",
        incident_start_time_utc=datetime(2026, 1, 1),
        environment="Public",
        # ... add TSG-specific defaults ...
    )
    defaults.update(overrides)
    return <TsgName>Input(**defaults)


def _make_incident(title: str, create_date: datetime = None) -> MagicMock:
    incident = MagicMock()
    incident.Title = title
    incident.Summary = ""
    incident.CreateDate = create_date or datetime(2026, 1, 1)
    incident.Descriptions = []
    return incident


# ── Test: _extract_input_from_incident ───────────────────────


class TestExtractInputFromIncident:
    """Test _extract_input_from_incident with example titles."""

    async def test_extracts_from_typical_title(self):
        tsg = _make_tsg()
        incident = _make_incident("<example title from TSG analysis>")
        result = await tsg._extract_input_from_incident("123", incident)
        assert result.tenant_name == "<expected>"

    async def test_raises_when_field_missing(self):
        tsg = _make_tsg()
        incident = _make_incident("No useful info here")
        with pytest.raises(ValueError) as ctx:
            await tsg._extract_input_from_incident("123", incident)
        assert "tenant_name" in str(ctx.value)


# ── Test: step methods ───────────────────────────────────────


class TestStep1<Name>:
    """Test step 1 with mocked DGrep data."""

    @patch("zerotoil.tsgs.<tsg_module>.dgrep")
    async def test_parses_expected_data(self, mock_dgrep):
        df = pd.DataFrame({...})  # Real data captured from DGrep
        mock_dgrep.query = AsyncMock(return_value=_make_dgrep_result(df))
        tsg = _make_tsg()
        await tsg._step_1_<name>(_make_input())
        assert tsg.<field> == "<expected>"

    @patch("zerotoil.tsgs.<tsg_module>.dgrep")
    async def test_handles_empty_results(self, mock_dgrep):
        mock_dgrep.query = AsyncMock(return_value=_make_dgrep_result(pd.DataFrame()))
        tsg = _make_tsg()
        await tsg._step_1_<name>(_make_input())
        assert tsg.<field> == ""  # or appropriate default


# ── Test: end-to-end _run ────────────────────────────────────


class TestEndToEnd<Scenario>:
    """Test the full TSG _run with all steps mocked."""

    @patch("zerotoil.tsgs.<tsg_module>.icm")
    @patch("zerotoil.tsgs.<tsg_module>.dgrep")
    async def test_happy_path(self, mock_dgrep, mock_icm):
        mock_dgrep.query = AsyncMock(side_effect=[...])
        mock_icm.get_incident = AsyncMock(return_value=_make_incident("..."))
        # ... setup all mocks ...

        tsg = _make_tsg()
        result = await tsg._run(_make_input())

        assert result.is_completed
        assert result.mitigation_status == "NoActionNeeded"

    @patch("zerotoil.tsgs.<tsg_module>.dgrep")
    async def test_manual_action_path(self, mock_dgrep):
        mock_dgrep.query = AsyncMock(side_effect=[...])
        tsg = _make_tsg()
        with pytest.raises(ManualActionRequired) as ctx:
            await tsg._run(_make_input())
        assert "escalate" in str(ctx.value).lower()
```

## What to test for each TSG

| Component | What to verify | Coverage goals |
|---|---|---|
| `_extract_input_from_incident` | Regex/LLM extraction from title, fallback to descriptions, error on missing fields | Multiple title formats, sovereign cloud variants, edge cases |
| `_step_N_*` methods | Correct parsing of DGrep/Kusto DataFrames, intermediate state set correctly | Happy path, empty results, missing columns, column casing |
| `_run()` end-to-end | Full pipeline with all steps mocked | Completed path, not-completed path, manual escalation path |
| Helper functions | `_stage_index`, custom parsers, mapping functions | All known inputs, unknown inputs, edge cases |
| Cross-TSG calls | Mock the sub-TSG's `.run()` and verify input construction | Input forwarding, result handling |
| Manual steps | Verify `ManualActionRequired` is raised with the right message | Escalation messages, contact info |

## Constructing mock data from real sources

**The best unit tests use real data** — captured from actual DGrep queries, ICM incidents, and XDS logs, then embedded as mock DataFrames. This catches parsing bugs that synthetic data misses.

### How to capture real data for mocks

1. **Use MCP tools** (DGrep, ICM, Kusto) to query real data for a representative incident.
2. **Use `run_python_code`** to execute queries and capture DataFrame outputs.
3. **Copy the column names and values** directly into `pd.DataFrame({...})` in the test.
4. **Sanitize**: replace real account names/IDs with placeholders if they appear in assertions, but keep realistic data structure.

### Converting DGrep output to test DataFrames

1. **Read the column names** from the printed header (these are the schema-native names).
2. **Copy each row's values** into Python lists.
3. **Build `pd.DataFrame({...})`** with the exact column names and values.
4. **Note split rows** — some log messages span multiple DataFrame rows. Each row is an independent entry.

Example from real output:
```
message             PreciseTimeStamp                           activityId
[AccountFailover]...  2026-03-21T00:21:36.9227893Z cb492a9c-68db-...
[metric:Failover...   2026-03-21T00:21:36.9228197Z cb492a9c-68db-...
```

Becomes:
```python
pd.DataFrame({
    "message": [
        "[AccountFailover]...",  # full text from real output
        "[metric:Failover...",   # full text from real output
    ],
    "PreciseTimeStamp": [
        "2026-03-21T00:21:36.9227893Z",
        "2026-03-21T00:21:36.9228197Z",
    ],
    "activityId": [
        "cb492a9c-68db-...",
        "cb492a9c-68db-...",
    ],
})
```

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Async tests not collected | Class inherits from `unittest.IsolatedAsyncioTestCase` | Remove inheritance — use plain class |
| `self.assertEqual` gives poor error messages | Using unittest assertion style | Use plain `assert a == b` |
| Async tests deselected by `-m unittest` | Auto-marker checked for *any* marker, not just category markers | Ensure `conftest.py` checks only for `_CATEGORY_MARKERS` |
| `ctx.exception` AttributeError | Using unittest-style `assertRaises` context | Use `pytest.raises()` with `ctx.value` |
| Tests pass locally but fail in CI | Different Python version or missing mock setup | Run `pytest -v` locally in `.venv`; check mock `side_effect` covers all queries |
| Shared state between tests | TSG class-level mutable defaults (e.g., `dgrep_links = []`) | Create fresh TSG instances and set `tsg.dgrep_links = []` per test |

## Reference implementation

See [tests/tsgs/test_failover_pending_transaction.py](../../tests/tsgs/test_failover_pending_transaction.py) for a complete working example with 36 tests covering:
- `_stage_index` helper (4 tests)
- `_extract_input_from_incident` with 8 title variants including sovereign clouds
- Step 1 parsing with real DGrep data (6 tests: column casing, fallback query, empty results)
- Step 2 completion detection (3 tests)
- Step 3 stage classification (5 tests)
- End-to-end `_run()` completed path (2 tests)
- End-to-end `_run()` not-completed path with manual escalation (2 tests)
- Branch B: PollFailover secondary analysis (5 tests)
- Cross-incident validation (1 test)
