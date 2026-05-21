"""Unit tests for FailoverPendingTransaction TSG.

Tests parsing logic and incident input extraction using real DGrep data
from incidents 765813207 and 770004255 (RSRPAustraliaEast).

Run:
    cd zero-toil
    pytest tests/tsgs/test_failover_pending_transaction.py -v
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pandas as pd

from zerotoil.tsgs.failover_pending_transaction import (
    FailoverPendingTransaction,
    FailoverPendingTransactionInput,
    ManualActionRequired,
    _FINALIZE_STAGES,
    _stage_index,
)


# ── Helpers ──────────────────────────────────────────────────


def _make_dgrep_result(df: pd.DataFrame) -> MagicMock:
    """Create a mock DGrep query result with .to_df() and .get_dgrep_link()."""
    result = MagicMock()
    result.to_df.return_value = df
    result.get_dgrep_link.return_value = "https://fake-dgrep-link"
    return result


def _make_xds_result(df: pd.DataFrame) -> MagicMock:
    """Create a mock XDS log search result with .to_df()."""
    result = MagicMock()
    result.to_df.return_value = df
    return result


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Patch asyncio.sleep to be instant in all tests."""
    async def _instant_sleep(_seconds):
        pass
    monkeypatch.setattr("asyncio.sleep", _instant_sleep)


def _make_account_entity(
    tenant_name: str = "MS-SYD24PrdStr02A",
    geo_pair_name: str = "MS-MEL23PrdStr11D",
    account_type: str = "GRS",
) -> MagicMock:
    """Build a mock account entity returned by get_account()."""
    entity = MagicMock()
    entity.TenantName = tenant_name
    entity.GeoPairName = geo_pair_name
    entity.AccountType = account_type
    return entity


def _make_incident(
    title: str,
    create_date: datetime = None,
    descriptions: list = None,
) -> MagicMock:
    """Build a mock ICM incident object."""
    incident = MagicMock()
    incident.Title = title
    incident.Summary = ""
    incident.CreateDate = create_date or datetime(2026, 3, 20, 23, 58, 57, 750000)
    incident.Descriptions = descriptions or []
    return incident


def _make_tsg() -> FailoverPendingTransaction:
    """Create a fresh TSG instance with clean state."""
    tsg = FailoverPendingTransaction()
    # Instance-level list to avoid mutating the shared class attribute
    tsg.dgrep_links = []
    return tsg


def _make_input(**overrides) -> FailoverPendingTransactionInput:
    """Build the standard test input (incident 765813207)."""
    defaults = dict(
        incident_id="765813207",
        tenant_name="RSRPAustraliaEast",
        incident_start_time_utc=datetime(2026, 3, 20, 23, 58, 57, 750000),
        environment="Public",
    )
    defaults.update(overrides)
    return FailoverPendingTransactionInput(**defaults)


def _make_dgrep_query_side_effect(
    step1_df: pd.DataFrame,
    step2_df: pd.DataFrame = None,
    step3_df: pd.DataFrame = None,
    fallback_step1_stats_df: pd.DataFrame = None,
):
    """Build a DGrep AsyncMock side-effect aware of event/query purpose.

    Step 1 now issues multiple chunked ServiceBackgroundActivityEvent queries,
    so tests should route by event type instead of relying on fixed call counts.
    """

    async def _side_effect(*args, **kwargs):
        event_name = kwargs.get("event_names")
        server_query = kwargs.get("server_query", "")

        if event_name == "ServiceBackgroundActivityEvent":
            return _make_dgrep_result(step1_df.copy())

        if event_name == "AccountFailoverEvent":
            if step2_df is None:
                raise AssertionError("Unexpected AccountFailoverEvent query in test")
            return _make_dgrep_result(step2_df.copy())

        if event_name == "AccountFailoverStatisticsEvent":
            if "PrimaryStage" in server_query or "SecondaryStage" in server_query:
                if step3_df is None:
                    raise AssertionError("Unexpected stage query in test")
                return _make_dgrep_result(step3_df.copy())

            if fallback_step1_stats_df is not None:
                return _make_dgrep_result(fallback_step1_stats_df.copy())

            if step3_df is not None:
                return _make_dgrep_result(step3_df.copy())

            raise AssertionError("Unexpected AccountFailoverStatisticsEvent query in test")

        raise AssertionError(f"Unexpected DGrep event: {event_name}")

    return _side_effect


# ── Real DGrep data from incident 765813207 ─────────────────
#
# DGrep returns schema-native column names (lowercase "message",
# mixed-case "PreciseTimeStamp", camelCase "activityId") regardless
# of how they are spelled in the MQL select clause.

STEP1_ALERT_DF = pd.DataFrame({
    "message": [
        (
            "[AccountFailover] [PendingFailoverOperation] "
            "[OperationId: 911d7400-323c-4858-a2c4-dae86475555c, "
            "account name: ppthdprodFailoverType: Soft, "
            "StartTimeInUtc: 3/20/2026 10:38:59 PM] "
            "Failover has been flagged and alerted for SLA breach."
        ),
        (
            "[metric:FailoverTransactionSLABreachMetric. "
            "dimensionValues: SecondaryStuck.PrepareFailover"
        ),
        (
            "[AccountFailover] [PendingFailoverOperation] "
            "[OperationId: 911d7400-323c-4858-a2c4-dae86475555c, "
            "account name: ppthdprodFailoverType: Soft, "
            "StartTimeInUtc: 3/20/2026 10:38:59 PM] "
            "Failover has been flagged and alerted for SLA breach."
        ),
        (
            "[metric:FailoverTransactionSLABreachMetric. "
            "dimensionValues: SecondaryStuck.PrepareFailover"
        ),
    ],
    "PreciseTimeStamp": [
        "2026-03-21T00:21:36.9227893Z",
        "2026-03-21T00:21:36.9228197Z",
        "2026-03-20T23:52:03.7938753Z",
        "2026-03-20T23:52:03.7939201Z",
    ],
    "activityId": [
        "cb492a9c-68db-4da0-843e-b94ef56a9787",
        "cb492a9c-68db-4da0-843e-b94ef56a9787",
        "8cf9e5e7-c377-4826-8f97-0d79a0b69974",
        "8cf9e5e7-c377-4826-8f97-0d79a0b69974",
    ],
})


# ── Test: _stage_index ───────────────────────────────────────


class TestStageIndex:
    """Test the _stage_index helper function."""

    def test_known_stages(self):
        assert _stage_index("NotStarted") == 0
        assert _stage_index("PrepareFailover") == 1
        assert _stage_index("PollFailover") == 2
        assert _stage_index("FinalizeFailover") == 3
        assert _stage_index("SoftFinalizeFailover") == 4
        assert _stage_index("HardFinalizeFailover") == 5
        assert _stage_index("PollFinalizeFailover") == 6
        assert _stage_index("DnsSwitch") == 7
        assert _stage_index("ShortTermCleanup") == 8

    def test_case_insensitive(self):
        assert _stage_index("preparefailover") == 1
        assert _stage_index("PREPAREFAILOVER") == 1

    def test_unknown_stage(self):
        assert _stage_index("UnknownStage") == -1
        assert _stage_index("") == -1

    def test_whitespace_handling(self):
        assert _stage_index("  PrepareFailover  ") == 1


# ── Test: _extract_input_from_incident ───────────────────────


class TestExtractInputFromIncident:
    """Test _extract_input_from_incident with example incident titles."""

    async def test_extracts_tenant_from_full_title(self):
        tsg = _make_tsg()
        incident = _make_incident(
            "[FailoverPendingTransaction] Failover pending for account stuck on "
            "PrimaryStuck.PrepareFailover in RSRPWestEurope"
        )
        result = await tsg._extract_input_from_incident("123", incident)
        assert result.tenant_name == "RSRPWestEurope"
        assert result.environment == "Production"

    async def test_extracts_tenant_from_short_title(self):
        tsg = _make_tsg()
        incident = _make_incident(
            "[FailoverPendingTransaction] PrimaryStuck.PrepareFailover in RSRPEastUS2"
        )
        result = await tsg._extract_input_from_incident("456", incident)
        assert result.tenant_name == "RSRPEastUS2"

    async def test_extracts_sovereign_cloud_ussec(self):
        tsg = _make_tsg()
        incident = _make_incident(
            "[FailoverPendingTransaction] PrimaryStuck.PrepareFailover "
            "in RSRPUSSec01 (USSec)"
        )
        result = await tsg._extract_input_from_incident("789", incident)
        assert result.tenant_name == "RSRPUSSec01"
        assert result.environment == "USSec"

    async def test_extracts_sovereign_cloud_usnat(self):
        tsg = _make_tsg()
        incident = _make_incident(
            "[FailoverPendingTransaction] PrimaryStuck.PrepareFailover "
            "in RSRPUSNat01 (USNat)"
        )
        result = await tsg._extract_input_from_incident("790", incident)
        assert result.environment == "USNat"

    async def test_uses_create_date_as_start_time(self):
        tsg = _make_tsg()
        dt = datetime(2026, 3, 20, 23, 58, 57, 750000)
        incident = _make_incident(
            "[FailoverPendingTransaction] in RSRPAustraliaEast",
            create_date=dt,
        )
        result = await tsg._extract_input_from_incident("123", incident)
        assert result.incident_start_time_utc == dt

    async def test_fallback_to_descriptions(self):
        tsg = _make_tsg()
        desc = MagicMock()
        desc.Text = "Failover stuck in RSRPSouthEastAsia"
        incident = _make_incident(
            "Some generic title without tenant",
            descriptions=[desc],
        )
        result = await tsg._extract_input_from_incident("999", incident)
        assert result.tenant_name == "RSRPSouthEastAsia"

    async def test_raises_when_tenant_not_found(self):
        tsg = _make_tsg()
        incident = _make_incident("No tenant info here at all")
        with pytest.raises(ValueError) as ctx:
            await tsg._extract_input_from_incident("111", incident)
        assert "tenant_name" in str(ctx.value)

    async def test_real_incident_765813207_title(self):
        """Reproduce exact title pattern from incident 765813207."""
        tsg = _make_tsg()
        incident = _make_incident(
            "[Monitor:FailoverPendingTransaction] Failover Pending Transaction "
            "alert for pending failover operation stuck on "
            "SecondaryStuck.PrepareFailover in RSRPAustraliaEast"
        )
        result = await tsg._extract_input_from_incident("765813207", incident)
        assert result.tenant_name == "RSRPAustraliaEast"
        assert result.environment == "Production"


# ── Test: Step 1 — extract failover context ──────────────────


class TestStep1ExtractFailoverContext:
    """Test step 1 parsing with real DGrep data from incident 765813207.

    The DGrep mock returns schema-native column names (lowercase "message")
    rather than the MQL alias ("Message").  This is the exact bug scenario.
    """

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_extracts_operation_id_and_account(self, mock_dgrep):
        """Real DGrep data → correctly extracts OperationId and account name."""
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(STEP1_ALERT_DF.copy()),
        )

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        assert tsg.operation_id == "911d7400-323c-4858-a2c4-dae86475555c"
        assert tsg.account_name == "ppthdprod"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_works_with_uppercase_column_names(self, mock_dgrep):
        """Even if DGrep returns uppercase 'Message', parsing still works."""
        df_upper = STEP1_ALERT_DF.copy().rename(columns={"message": "Message"})
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df_upper),
        )

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        assert tsg.operation_id == "911d7400-323c-4858-a2c4-dae86475555c"
        assert tsg.account_name == "ppthdprod"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_handles_empty_results(self, mock_dgrep):
        """Empty DGrep results → fields stay empty, no crash."""
        empty_df = pd.DataFrame(
            columns=["message", "PreciseTimeStamp", "activityId"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        assert tsg.operation_id == ""
        assert tsg.account_name == ""

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_populates_dgrep_links(self, mock_dgrep):
        """DGrep evidence links are collected."""
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(STEP1_ALERT_DF.copy()),
        )

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        assert len(tsg.dgrep_links) >= 1
        assert tsg.dgrep_links[0] == "https://fake-dgrep-link"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_fallback_second_query_for_account(self, mock_dgrep):
        """When account name is missing from alert, falls back to second query."""
        # Remove the "account name:" pattern so first parse misses it
        df_no_acct = STEP1_ALERT_DF.copy()
        df_no_acct["message"] = df_no_acct["message"].str.replace(
            "account name:", "acct:", regex=False,
        )

        stats_df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-21T00:21:36.9227893Z"],
            "accountName": ["mystorageaccount"],
            "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
        })

        async def _query_side_effect(*args, **kwargs):
            event_names = kwargs.get("event_names")
            if event_names == "AccountFailoverStatisticsEvent":
                return _make_dgrep_result(stats_df)
            return _make_dgrep_result(df_no_acct)

        mock_dgrep.query = AsyncMock(side_effect=_query_side_effect)

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        assert tsg.operation_id == "911d7400-323c-4858-a2c4-dae86475555c"
        assert tsg.account_name == "mystorageaccount"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_uses_minus_3h_to_plus_30m_window_in_chunks(self, mock_dgrep):
        """Step 1 starts at -3h and ends at +30m using 30-minute chunks."""
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(STEP1_ALERT_DF.copy()),
        )

        tsg = _make_tsg()
        tsg_input = _make_input()
        await tsg._step_1_extract_failover_context(tsg_input)

        expected_from = tsg_input.incident_start_time_utc - timedelta(hours=3)
        expected_to = tsg_input.incident_start_time_utc + timedelta(minutes=30)

        first_call = mock_dgrep.query.await_args_list[0].kwargs
        last_call = mock_dgrep.query.await_args_list[6].kwargs

        assert first_call["from_time"] == expected_from
        assert first_call["to_time"] == expected_from + timedelta(minutes=30)
        assert last_call["from_time"] == expected_to - timedelta(minutes=30)
        assert last_call["to_time"] == expected_to

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_ignores_failed_chunk_and_merges_successful_chunks(self, mock_dgrep):
        """One throttled chunk is skipped while successful chunks are still used."""
        success_df = STEP1_ALERT_DF.copy()
        call_counter = {"value": 0}

        async def _query_side_effect(*args, **kwargs):
            call_counter["value"] += 1
            if call_counter["value"] == 1:
                raise RuntimeError("throttled")
            return _make_dgrep_result(success_df)

        mock_dgrep.query = AsyncMock(side_effect=_query_side_effect)

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        # We still parse the expected operation/account from successful chunks.
        assert tsg.operation_id == "911d7400-323c-4858-a2c4-dae86475555c"
        assert tsg.account_name == "ppthdprod"
        # At least one successful chunk should produce an evidence link.
        assert len(tsg.dgrep_links) >= 1

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_only_parses_rows_with_operation_id(self, mock_dgrep):
        """Rows without OperationId (metric rows) are skipped cleanly."""
        # Include only metric rows — no OperationId present
        metric_only_df = pd.DataFrame({
            "message": [
                "[metric:FailoverTransactionSLABreachMetric. "
                "dimensionValues: SecondaryStuck.PrepareFailover",
                "[metric:FailoverTransactionSLABreachMetric. "
                "dimensionValues: SecondaryStuck.PrepareFailover",
            ],
            "PreciseTimeStamp": [
                "2026-03-21T00:21:36.9228197Z",
                "2026-03-20T23:52:03.7939201Z",
            ],
            "activityId": [
                "cb492a9c-68db-4da0-843e-b94ef56a9787",
                "8cf9e5e7-c377-4826-8f97-0d79a0b69974",
            ],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(metric_only_df),
        )

        tsg = _make_tsg()
        await tsg._step_1_extract_failover_context(_make_input())

        assert tsg.operation_id == ""


# ── Test: Step 2 — check failover completion ─────────────────


class TestStep2CheckFailoverCompletion:
    """Test step 2 completion-check logic with mocked DGrep data."""

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_detects_completed_failover(self, mock_dgrep):
        df = pd.DataFrame({
            "PreciseTimeStamp": [
                "2026-03-20T23:59:00Z",
                "2026-03-21T00:10:00Z",
            ],
            "accountName": ["ppthdprod", "ppthdprod"],
            "accountFailoverStatusType": ["InProgress", "Complete"],
            "operationId": ["op1", "op1"],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df),
        )

        tsg = _make_tsg()
        tsg.account_name = "ppthdprod"
        await tsg._step_2_check_failover_completion(_make_input())

        assert tsg.is_completed

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_not_completed_when_in_progress(self, mock_dgrep):
        df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-21T00:10:00Z"],
            "accountName": ["ppthdprod"],
            "accountFailoverStatusType": ["InProgress"],
            "operationId": ["op1"],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df),
        )

        tsg = _make_tsg()
        tsg.account_name = "ppthdprod"
        await tsg._step_2_check_failover_completion(_make_input())

        assert not tsg.is_completed

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_skips_when_no_account_name(self, mock_dgrep):
        tsg = _make_tsg()
        tsg.account_name = ""
        await tsg._step_2_check_failover_completion(_make_input())

        assert not tsg.is_completed
        mock_dgrep.query.assert_not_called()


# ── Test: Step 3 — determine stuck stage ─────────────────────


class TestStep3DetermineStuckStage:
    """Test step 3 stage classification with mocked DGrep data."""

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_primary_behind_secondary(self, mock_dgrep):
        """Primary at PrepareFailover, Secondary at PollFailover → Primary stuck."""
        df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-21T00:10:00Z"],
            "accountName": ["ppthdprod"],
            "PrimaryStage": ["PrepareFailover"],
            "SecondaryStage": ["PollFailover"],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df),
        )

        tsg = _make_tsg()
        tsg.account_name = "ppthdprod"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Primary"
        assert tsg.stuck_stage == "PrepareFailover"
        assert tsg.primary_stage == "PrepareFailover"
        assert tsg.secondary_stage == "PollFailover"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_secondary_behind_primary(self, mock_dgrep):
        """Secondary at PrepareFailover, Primary at FinalizeFailover → Secondary stuck."""
        df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-21T00:10:00Z"],
            "accountName": ["ppthdprod"],
            "PrimaryStage": ["FinalizeFailover"],
            "SecondaryStage": ["PrepareFailover"],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df),
        )

        tsg = _make_tsg()
        tsg.account_name = "ppthdprod"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Secondary"
        assert tsg.stuck_stage == "PrepareFailover"
        assert tsg.primary_stage == "FinalizeFailover"
        assert tsg.secondary_stage == "PrepareFailover"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_unknown_when_stages_equal(self, mock_dgrep):
        df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-21T00:10:00Z"],
            "accountName": ["ppthdprod"],
            "PrimaryStage": ["PrepareFailover"],
            "SecondaryStage": ["PrepareFailover"],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df),
        )

        tsg = _make_tsg()
        tsg.account_name = "ppthdprod"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Unknown"
        assert tsg.primary_stage == "PrepareFailover"
        assert tsg.secondary_stage == "PrepareFailover"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_unknown_when_no_data(self, mock_dgrep):
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        tsg.account_name = "ppthdprod"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Unknown"
        assert tsg.stuck_stage == "Unknown"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_skips_when_no_account(self, mock_dgrep):
        tsg = _make_tsg()
        tsg.account_name = ""
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Unknown"
        mock_dgrep.query.assert_not_called()


# ── Real DGrep data from incident 770004255 ──────────────────
# Title: "[FailoverPendingTransaction] Failover for accounts stuck on
#          SecondaryStuck.PollFinalizeFailover in RSRPAustraliaEast"
# CreateDate: 2026-03-28 15:49:09.400000
# Outcome: Failover already completed → Steps 3-4 skipped → Step 5

INCIDENT_770004255_STEP1_DF = pd.DataFrame({
    "PreciseTimeStamp": [
        "2026-03-28T15:41:16.7901803Z",
        "2026-03-28T15:41:16.7902141Z",
        "2026-03-28T14:40:56.4706935Z",
        "2026-03-28T14:40:56.4707383Z",
        "2026-03-28T14:11:37.4859142Z",
        "2026-03-28T14:11:37.4859142Z",
    ],
    "activityId": [
        "b9e3b405-a743-460b-8c44-e83a7b02d095",
        "b9e3b405-a743-460b-8c44-e83a7b02d095",
        "21cc55f9-72ac-4520-a6e4-eea4992e7c92",
        "21cc55f9-72ac-4520-a6e4-eea4992e7c92",
        "e47bb097-88c5-4b12-9e91-1047d620bba5",
        "e47bb097-88c5-4b12-9e91-1047d620bba5",
    ],
    "message": [
        (
            "[AccountFailover] [PendingFailoverOperation] "
            "[OperationId: 911d7400-323c-4858-a2c4-dae86475555c, "
            "account name: ppthdprodFailoverType: Soft, "
            "StartTimeInUtc: 3/20/2026 10:38:59 PM] "
            "Failover has been flagged and alerted for SLA breach."
        ),
        (
            "[metric:FailoverTransactionSLABreachMetric. "
            "dimensionValues: SecondaryStuck.PollFinalizeFailover"
        ),
        (
            "[AccountFailover] [PendingFailoverOperation] "
            "[OperationId: 911d7400-323c-4858-a2c4-dae86475555c, "
            "account name: ppthdprodFailoverType: Soft, "
            "StartTimeInUtc: 3/20/2026 10:38:59 PM] "
            "Failover has been flagged and alerted for SLA breach."
        ),
        (
            "[metric:FailoverTransactionSLABreachMetric. "
            "dimensionValues: SecondaryStuck.PrepareFailover"
        ),
        (
            "[AccountFailover] [PendingFailoverOperation] "
            "[OperationId: 911d7400-323c-4858-a2c4-dae86475555c, "
            "account name: ppthdprodFailoverType: Soft, "
            "StartTimeInUtc: 3/20/2026 10:38:59 PM] "
            "Failover has been flagged and alerted for SLA breach."
        ),
        (
            "[metric:FailoverTransactionSLABreachMetric. "
            "dimensionValues: SecondaryStuck.PrepareFailover"
        ),
    ],
})

INCIDENT_770004255_STEP2_COMPLETE_DF = pd.DataFrame({
    "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
    "accountName": ["ppthdprod"],
    "accountFailoverStatusType": ["Complete"],
    "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
})


def _make_input_770004255(**overrides) -> FailoverPendingTransactionInput:
    """Build test input for incident 770004255."""
    defaults = dict(
        incident_id="770004255",
        tenant_name="RSRPAustraliaEast",
        incident_start_time_utc=datetime(2026, 3, 28, 15, 49, 9, 400000),
        environment="Public",
    )
    defaults.update(overrides)
    return FailoverPendingTransactionInput(**defaults)


def _make_incident_770004255() -> MagicMock:
    """Build mock ICM incident for 770004255."""
    return _make_incident(
        title=(
            "[FailoverPendingTransaction] Failover for accounts stuck on "
            "SecondaryStuck.PollFinalizeFailover in RSRPAustraliaEast"
        ),
        create_date=datetime(2026, 3, 28, 15, 49, 9, 400000),
    )


# ── Test: End-to-end with real data (incident 770004255) ─────


class TestEndToEndCompleted:
    """End-to-end test: failover already completed (incident 770004255).

    This test exercises the full _run() path:
      Step 1 → extracts operation_id + account_name
      Step 2 → detects completion
      Steps 3-4 → skipped
      Step 5 → posts evidence to ICM, mitigate gracefully handled
    """

    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_completed_failover_path(self, mock_dgrep, mock_icm):
        # -- Arrange DGrep mocks --
        mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
            step1_df=INCIDENT_770004255_STEP1_DF,
            step2_df=INCIDENT_770004255_STEP2_COMPLETE_DF,
        ))

        # -- Arrange ICM mock --
        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.mitigate = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        # -- Act --
        tsg = _make_tsg()
        result = await tsg._run(_make_input_770004255())

        # -- Assert output --
        assert result.account_name == "ppthdprod"
        assert result.operation_id == "911d7400-323c-4858-a2c4-dae86475555c"
        assert result.is_completed
        assert result.mitigation_status == "NoActionNeeded"
        assert result.stuck_location == ""
        assert result.stuck_stage == ""

        # Step 5 should have posted evidence
        mock_incident.add_description.assert_called_once()
        evidence_text = mock_incident.add_description.call_args[0][0]
        assert "ppthdprod" in evidence_text
        assert "Failover completed:</b> True" in evidence_text

        # Mitigate should have been attempted
        mock_incident.mitigate.assert_called_once()

        # Step 1 is chunked, so total call count can be > 2.
        called_events = [c.kwargs.get("event_names") for c in mock_dgrep.query.await_args_list]
        assert "ServiceBackgroundActivityEvent" in called_events
        assert "AccountFailoverEvent" in called_events

    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_completed_failover_mitigate_fails_gracefully(self, mock_dgrep, mock_icm):
        """If ICM mitigate() throws, the TSG should not crash."""
        mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
            step1_df=INCIDENT_770004255_STEP1_DF,
            step2_df=INCIDENT_770004255_STEP2_COMPLETE_DF,
        ))

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.mitigate = AsyncMock(
            side_effect=Exception("400 Bad Request — already mitigated")
        )
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        # Should not raise
        result = await tsg._run(_make_input_770004255())

        assert result.is_completed
        assert result.mitigation_status == "NoActionNeeded"


class TestEndToEndNotCompleted:
    """End-to-end test: failover NOT completed → goes through Steps 3-4."""

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_prepare_failover_stuck_no_pattern(self, mock_dgrep, mock_xds, mock_icm, mock_get_account):
        """PrepareFailover stuck, no known TableMaster pattern → default escalation."""
        mock_get_account.return_value = _make_account_entity()
        not_complete_df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
            "accountName": ["ppthdprod"],
            "accountFailoverStatusType": ["InProgress"],
            "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
        })
        stage_df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
            "accountName": ["ppthdprod"],
            "PrimaryStage": ["PrepareFailover"],
            "SecondaryStage": ["PollFailover"],
        })

        mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
            step1_df=INCIDENT_770004255_STEP1_DF,
            step2_df=not_complete_df,
            step3_df=stage_df,
        ))

        # XDS mocks (Branch A — no split failures found)
        # XDS search_log returns an object with .to_df()
        xac_mock_result = MagicMock()
        xac_mock_result.to_df.return_value = pd.DataFrame(
            columns=["componentName", "level", "timestamp", "module",
                     "component", "message", "activityId"]
        )
        tm_mock_result = MagicMock()
        tm_mock_result.to_df.return_value = pd.DataFrame(
            columns=["componentName", "level", "timestamp", "module",
                     "component", "message", "activityId"]
        )
        mock_xds.search_log = AsyncMock(side_effect=[xac_mock_result, tm_mock_result])
        mock_xds.generate_log_search_link = AsyncMock(return_value="https://fake-xds-link")

        # ICM mock — escalation will raise ManualActionRequired
        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_input_770004255())

        assert result.mitigation_status == "Escalated"
        assert ("ximi@microsoft.com" in tsg.mitigation_detail) or ("XGeo DRI" in tsg.mitigation_detail)
        assert tsg.stuck_location == "Primary"
        assert tsg.stuck_stage == "PrepareFailover"
        assert tsg.mitigation_status == "Escalated"

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_prepare_failover_llam_split_block(self, mock_dgrep, mock_xds, mock_icm, mock_get_account):
        """PrepareFailover stuck with LLAM split block → transfer to StorageCRM."""
        mock_get_account.return_value = _make_account_entity()
        not_complete_df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
            "accountName": ["ppthdprod"],
            "accountFailoverStatusType": ["InProgress"],
            "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
        })
        stage_df = pd.DataFrame({
            "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
            "accountName": ["ppthdprod"],
            "PrimaryStage": ["PrepareFailover"],
            "SecondaryStage": ["NotStarted"],
        })

        mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
            step1_df=INCIDENT_770004255_STEP1_DF,
            step2_df=not_complete_df,
            step3_df=stage_df,
        ))

        # XDS: TableMaster has LLAM split block
        xac_mock = MagicMock()
        xac_mock.to_df.return_value = pd.DataFrame(
            columns=["componentName", "level", "timestamp", "module",
                     "component", "message", "activityId"]
        )
        tm_mock = MagicMock()
        tm_mock.to_df.return_value = pd.DataFrame({
            "message": [
                "Cannot split partition T123 for account ppthdprod: "
                "Incompatible LLAM Stage detected on replica"
            ],
            "timestamp": ["2026-03-28T15:00:00Z"],
            "activityId": ["abc-123"],
            "componentName": ["xtablemaster"],
            "level": ["Error"],
            "module": ["SplitManager"],
            "component": ["PartitionSplit"],
        })
        mock_xds.search_log = AsyncMock(side_effect=[xac_mock, tm_mock])
        mock_xds.generate_log_search_link = AsyncMock(return_value="https://fake-xds-link")

        # ICM transfer mock
        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.transfer = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        # Transfer calls _transfer_incident which does NOT raise ManualActionRequired
        # It completes normally after the transfer
        result = await tsg._run(_make_input_770004255())

        assert tsg.mitigation_status == "Transferred"
        assert "LLAM" in tsg.xds_evidence_summary
        mock_incident.transfer.assert_called_once()
        transfer_kwargs = mock_incident.transfer.call_args[1]
        assert transfer_kwargs["tenant"] == "Xstore"
        assert transfer_kwargs["team"] == "StorageCRM"


# ── Real XDS data from incident 770004255 (Nephos.Account Perf) ──
#
# Collected via collect_xds_logs.py from stamp ms-syd24prdstr02a.
# These are Nephos.Account perf log entries showing PostFailoverCleanup
# operations with Status=InternalError (HttpStatusCode=500).
# Note: No PollFailover entries were present — the failover had
# already transitioned past PollFailover by the search window.
#
# DataFrame columns match XdsLogSearchEncapsulatedResult.to_df() schema.

NEPHOS_ACCOUNT_PERF_REAL_DF = pd.DataFrame({
    "componentName": [
        "ms-syd24prdstr02a$nephos.account_in_5",
        "ms-syd24prdstr02a$nephos.account_in_7",
        "ms-syd24prdstr02a$nephos.account_in_2",
    ],
    "level": ["perf", "perf", "perf"],
    "timestamp": [
        "2026-03-28 15:48:05.951280",
        "2026-03-28 15:48:06.991224",
        "2026-03-28 15:48:10.083448",
    ],
    "module": ["CsClient", "CsClient", "CsClient"],
    "component": ["NephosAccount.exe", "NephosAccount.exe", "NephosAccount.exe"],
    "srcFile": ["PerfCounterLogProcessor.cs"] * 3,
    "srcFunc": ["LogPerfCounter"] * 3,
    "srcLine": ["305"] * 3,
    "pid": ["34832", "61276", "72948"],
    "tid": ["38644", "28592", "75168"],
    "message": [
        (
            "Perf: PerfCounters: Account=ppthdprod Operation=PostFailoverCleanup "
            "on Container= with Status=InternalError RequestHeaderSize=5235 "
            "RequestSize=638 ResponseHeaderSize=163 ResponseSize=253 "
            "ErrorResponseByte=253 TimeInMs=125.000000 ProcessingTimeInMs=124.000000 "
            "HttpStatusCode=500 InternalStatus=ServerOtherError "
            "AuthenticationType='dSts'"
        ),
        (
            "Perf: PerfCounters: Account=ppthdprod Operation=PostFailoverCleanup "
            "on Container= with Status=InternalError RequestHeaderSize=5235 "
            "RequestSize=638 ResponseHeaderSize=163 ResponseSize=253 "
            "ErrorResponseByte=253 TimeInMs=21.000000 ProcessingTimeInMs=20.000000 "
            "HttpStatusCode=500 InternalStatus=ServerOtherError "
            "AuthenticationType='dSts'"
        ),
        (
            "Perf: PerfCounters: Account=ppthdprod Operation=PostFailoverCleanup "
            "on Container= with Status=InternalError RequestHeaderSize=5235 "
            "RequestSize=638 ResponseHeaderSize=163 ResponseSize=253 "
            "ErrorResponseByte=253 TimeInMs=18.000000 ProcessingTimeInMs=16.000000 "
            "HttpStatusCode=500 InternalStatus=ServerOtherError "
            "AuthenticationType='dSts'"
        ),
    ],
    "activityId": [
        "9AAF1420-0004-0005-71CA-BE042C000000",
        "E299E532-9004-0007-6BCA-BEBA94000000",
        "ED25B1DA-2004-0002-21CA-BE684F000000",
    ],
    "entryId": [None, None, None],
    "logFileName": [
        "cosmosPerfLog_NephosAccount.exe_002451.bin",
        "cosmosPerfLog_NephosAccount.exe_002397.bin",
        "cosmosPerfLog_NephosAccount.exe_002453.bin",
    ],
})

# Synthetic PollFailover perf entries (not from real data)
# Used to test the positive PollFailover detection path.
NEPHOS_ACCOUNT_PERF_POLLFAILOVER_DF = pd.DataFrame({
    "componentName": [
        "ms-syd24prdstr02a$nephos.account_in_5",
        "ms-syd24prdstr02a$nephos.account_in_7",
    ],
    "level": ["perf", "perf"],
    "timestamp": [
        "2026-03-28 15:48:05.951280",
        "2026-03-28 15:48:06.991224",
    ],
    "module": ["CsClient", "CsClient"],
    "component": ["NephosAccount.exe", "NephosAccount.exe"],
    "srcFile": ["PerfCounterLogProcessor.cs"] * 2,
    "srcFunc": ["LogPerfCounter"] * 2,
    "srcLine": ["305"] * 2,
    "pid": ["34832", "61276"],
    "tid": ["38644", "28592"],
    "message": [
        (
            "Perf: PerfCounters: Account=ppthdprod Operation=PollFailover "
            "on Container= with Status=InternalError RequestHeaderSize=5235 "
            "RequestSize=638 ResponseHeaderSize=163 ResponseSize=253 "
            "ErrorResponseByte=253 TimeInMs=125.000000 ProcessingTimeInMs=124.000000 "
            "HttpStatusCode=500 InternalStatus=ServerOtherError "
            "AuthenticationType='dSts'"
        ),
        (
            "Perf: PerfCounters: Account=ppthdprod Operation=PollFailover "
            "on Container= with Status=InternalError RequestHeaderSize=5235 "
            "RequestSize=638 ResponseHeaderSize=163 ResponseSize=253 "
            "ErrorResponseByte=253 TimeInMs=21.000000 ProcessingTimeInMs=20.000000 "
            "HttpStatusCode=500 InternalStatus=ServerOtherError "
            "AuthenticationType='dSts'"
        ),
    ],
    "activityId": [
        "9AAF1420-0004-0005-71CA-BE042C000000",
        "E299E532-9004-0007-6BCA-BEBA94000000",
    ],
    "entryId": [None, None],
    "logFileName": [
        "cosmosPerfLog_NephosAccount.exe_002451.bin",
        "cosmosPerfLog_NephosAccount.exe_002397.bin",
    ],
})

# Synthetic activity trace with GeoConfigOffCounter > 0
ACTIVITY_TRACE_GEOCONFIGOFF_DF = pd.DataFrame({
    "componentName": ["ms-syd24prdstr02a$nephos.account_in_5"],
    "level": ["verbose"],
    "timestamp": ["2026-03-28 15:48:05.951280"],
    "module": ["AccountManager"],
    "component": ["NephosAccount.exe"],
    "srcFile": ["AccountManager.cs"],
    "srcFunc": ["ProcessPollFailover"],
    "srcLine": ["1234"],
    "pid": ["34832"],
    "tid": ["38644"],
    "message": [
        "PollFailover for account ppthdprod: GeoConfigOffCounter=3 "
        "LastGeoConfigOffTime=2026-03-28T15:47:00Z"
    ],
    "activityId": ["9AAF1420-0004-0005-71CA-BE042C000000"],
    "entryId": [None],
    "logFileName": ["cosmosVerboseLog_NephosAccount.exe_002451.bin"],
})

# Synthetic activity trace WITHOUT GeoConfigOff (normal entries only)
ACTIVITY_TRACE_NO_GEOCONFIGOFF_DF = pd.DataFrame({
    "componentName": ["ms-syd24prdstr02a$nephos.account_in_5"],
    "level": ["verbose"],
    "timestamp": ["2026-03-28 15:48:05.951280"],
    "module": ["AccountManager"],
    "component": ["NephosAccount.exe"],
    "srcFile": ["AccountManager.cs"],
    "srcFunc": ["ProcessPollFailover"],
    "srcLine": ["1234"],
    "pid": ["34832"],
    "tid": ["38644"],
    "message": [
        "PollFailover for account ppthdprod: checking secondary status"
    ],
    "activityId": ["9AAF1420-0004-0005-71CA-BE042C000000"],
    "entryId": [None],
    "logFileName": ["cosmosVerboseLog_NephosAccount.exe_002451.bin"],
})


def _make_pollfailover_input(**overrides) -> FailoverPendingTransactionInput:
    """Build test input for a PollFailover-stuck-on-Secondary scenario."""
    defaults = dict(
        incident_id="770004255",
        tenant_name="RSRPAustraliaEast",
        incident_start_time_utc=datetime(2026, 3, 28, 15, 49, 9, 400000),
        environment="Public",
    )
    defaults.update(overrides)
    return FailoverPendingTransactionInput(**defaults)


# ── Test: Branch B — Both sides at PrepareFailover ─────────


def _make_both_preparefailover_input(**overrides) -> FailoverPendingTransactionInput:
    """Build test input where both sides are at PrepareFailover."""
    defaults = dict(
        incident_id="770004255",
        tenant_name="RSRPAustraliaEast",
        incident_start_time_utc=datetime(2026, 3, 28, 15, 49, 9, 400000),
        environment="Public",
    )
    defaults.update(overrides)
    return FailoverPendingTransactionInput(**defaults)


def _setup_dgrep_for_both_preparefailover(mock_dgrep):
    """Configure DGrep mocks so Step 3 returns both sides at PrepareFailover."""
    not_complete_df = pd.DataFrame({
        "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
        "accountName": ["ppthdprod"],
        "accountFailoverStatusType": ["InProgress"],
        "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
    })
    stage_df = pd.DataFrame({
        "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
        "accountName": ["ppthdprod"],
        "PrimaryStage": ["PrepareFailover"],
        "SecondaryStage": ["PrepareFailover"],
    })
    mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
        step1_df=INCIDENT_770004255_STEP1_DF,
        step2_df=not_complete_df,
        step3_df=stage_df,
    ))


class TestBranchBBothPrepareFailover:
    """Test Branch B: both sides at PrepareFailover → search Primary for GeoConfigOff."""

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_geoconfigoff_detected(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """GeoConfigOff found on Primary → escalate to ximi."""
        _setup_dgrep_for_both_preparefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity()

        # XDS: perf log with PollFailover + GeoConfigOff entries
        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(NEPHOS_ACCOUNT_PERF_POLLFAILOVER_DF.copy()),
        )
        mock_xds.search_by_activity_id = AsyncMock(
            return_value=_make_xds_result(ACTIVITY_TRACE_GEOCONFIGOFF_DF.copy()),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_preparefailover_input())

        assert result.mitigation_status == "Escalated"
        assert ("ximi@microsoft.com" in tsg.mitigation_detail) or ("XGeo DRI" in tsg.mitigation_detail)
        assert tsg.mitigation_status == "Escalated"
        assert "GeoConfigOff" in tsg.xds_evidence_summary
        assert tsg.primary_stage == "PrepareFailover"
        assert tsg.secondary_stage == "PrepareFailover"

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_no_geoconfigoff(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """PollFailover entries found but no GeoConfigOff → default escalation."""
        _setup_dgrep_for_both_preparefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity()

        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(NEPHOS_ACCOUNT_PERF_POLLFAILOVER_DF.copy()),
        )
        mock_xds.search_by_activity_id = AsyncMock(
            return_value=_make_xds_result(ACTIVITY_TRACE_NO_GEOCONFIGOFF_DF.copy()),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_preparefailover_input())

        assert result.mitigation_status == "Escalated"
        assert tsg.mitigation_status == "Escalated"
        assert "no GeoConfigOff" in tsg.xds_evidence_summary

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_empty_perf_log(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """No perf log entries → default escalation."""
        _setup_dgrep_for_both_preparefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity()

        empty_df = pd.DataFrame(
            columns=["componentName", "level", "timestamp", "module",
                     "component", "message", "activityId", "entryId",
                     "logFileName"],
        )
        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(empty_df),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_preparefailover_input())

        assert result.mitigation_status == "Escalated"
        assert tsg.mitigation_status == "Escalated"
        assert "no Nephos.Account perf logs" in tsg.xds_evidence_summary

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_searches_primary_tenant(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """Branch B searches the Primary (storage_tenant), not geo-pair."""
        _setup_dgrep_for_both_preparefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(NEPHOS_ACCOUNT_PERF_REAL_DF.copy()),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_preparefailover_input())

        assert result.mitigation_status == "Escalated"
        # Branch B searches Primary (storage_tenant), NOT geo-pair
        search_call = mock_xds.search_log.call_args
        assert search_call[0][0] == "MS-SYD24PrdStr02A"


# ── Test: Branch C — Both FinalizeFailover (XDS API escalation ladder) ──


def _make_xds_partition_result(partitions, continuation_key=None):
    """Build a mock XDS partition stats result.

    partitions: list of dicts with column values.
    """
    col_defs = [
        ("MetadataStreamName", 0),
        ("LowKey", 1),
        ("HighKey", 2),
        ("PartitionState", 5),
        ("StateMachineState", 6),
        ("GeoReplayerState", 399),
        ("GeoReceiverState", 398),
    ]

    # Build schema
    schema = MagicMock()
    columns = []
    for name, idx in col_defs:
        col = MagicMock()
        col.name = name
        columns.append(col)
    # Fill gaps with placeholder columns so indices match
    full_columns = []
    max_idx = max(idx for _, idx in col_defs)
    name_to_idx = {name: idx for name, idx in col_defs}
    for i in range(max_idx + 1):
        col = MagicMock()
        # Check if this index is a named column
        found = False
        for name, idx in col_defs:
            if idx == i:
                col.name = name
                found = True
                break
        if not found:
            col.name = f"_placeholder_{i}"
        full_columns.append(col)
    schema.columns = full_columns

    # Build rows
    rows = []
    for part in partitions:
        row = [None] * (max_idx + 1)
        for name, idx in col_defs:
            row[idx] = part.get(name, "")
        rows.append(row)

    result = MagicMock()
    result.schema = schema
    result.rows = rows
    result.continuation_key = continuation_key
    return result


def _make_both_finalizefailover_input(**overrides) -> FailoverPendingTransactionInput:
    """Build test input where both sides are at FinalizeFailover."""
    defaults = dict(
        incident_id="770004255",
        tenant_name="RSRPAustraliaEast",
        incident_start_time_utc=datetime(2026, 3, 28, 15, 49, 9, 400000),
        environment="Public",
    )
    defaults.update(overrides)
    return FailoverPendingTransactionInput(**defaults)


def _setup_dgrep_for_both_finalizefailover(mock_dgrep):
    """Configure DGrep mocks so Step 3 returns both sides at FinalizeFailover."""
    not_complete_df = pd.DataFrame({
        "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
        "accountName": ["ppthdprod"],
        "accountFailoverStatusType": ["InProgress"],
        "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
    })
    stage_df = pd.DataFrame({
        "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
        "accountName": ["ppthdprod"],
        "PrimaryStage": ["FinalizeFailover"],
        "SecondaryStage": ["FinalizeFailover"],
    })
    mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
        step1_df=INCIDENT_770004255_STEP1_DF,
        step2_df=not_complete_df,
        step3_df=stage_df,
    ))


class TestBranchCFinalizeFailover:
    """Test Branch C: both sides at FinalizeFailover → XDS API → Kusto → human fallback."""

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_xds_api_finds_live_replay(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """XDS API finds LiveReplay XFiles partitions → transfer to XStore/SMB."""
        _setup_dgrep_for_both_finalizefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.transfer = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        # Mock XDS API partition stats with LiveReplay partition
        api_result = _make_xds_partition_result([
            {
                "MetadataStreamName": "cosmos://ms-mel23prdstr11d/vol1/xtable/partitions/xfiles!20260418_test.meta",
                "LowKey": "[10000]TGId=0 0x0 ppthdprod\\x0101D5ED138BA96EA0;;0;0;",
                "HighKey": "[10000]TGId=0 0x0 ppthdprod\\x0101D5ED138BA96EA1;;0;0;",
                "PartitionState": "State_Normal",
                "StateMachineState": "GeoSend:StopSend;GeoReplay:LiveReplay;GeoReceive:LiveReceive",
                "GeoReplayerState": 102,
            },
        ])

        with patch(
            "zerotoil.tsgs.failover_pending_transaction.FailoverPendingTransaction._check_xfiles_partition_via_api",
            new_callable=AsyncMock,
            return_value=[{
                "MetadataStreamName": "xfiles!20260418_test.meta",
                "GeoReplayerState": 102,
                "StateMachineState": "GeoReplay:LiveReplay",
                "LowKey": "ppthdprod",
            }],
        ):
            tsg = _make_tsg()
            # Should transfer, not raise ManualActionRequired
            await tsg._run(_make_both_finalizefailover_input())

        assert tsg.mitigation_status == "Transferred"
        assert "LiveReplay" in tsg.xds_evidence_summary
        assert "SMB" in tsg.mitigation_detail
        mock_incident.transfer.assert_called_once()

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_xds_api_no_live_replay(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """XDS API succeeds but no LiveReplay partitions → default escalation."""
        _setup_dgrep_for_both_finalizefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity()

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        with patch(
            "zerotoil.tsgs.failover_pending_transaction.FailoverPendingTransaction._check_xfiles_partition_via_api",
            new_callable=AsyncMock,
            return_value=[],  # no LiveReplay found
        ):
            tsg = _make_tsg()
            result = await tsg._run(_make_both_finalizefailover_input())

        assert result.mitigation_status == "Escalated"
        assert tsg.mitigation_status == "Escalated"
        assert "no LiveReplay" in tsg.xds_evidence_summary

    @patch("zerotoil.tsgs.failover_pending_transaction.kusto")
    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_xds_api_fails_kusto_finds_live_replay(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account, mock_kusto,
    ):
        """XDS API fails → Kusto finds LiveReplay → transfer to XStore/SMB."""
        _setup_dgrep_for_both_finalizefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.transfer = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        # Kusto returns LiveReplay records
        kusto_df = pd.DataFrame({
            "MetadataStreamName": ["xfiles!20260418_test.meta"],
            "GeoReplayerState": [102],
            "LowKey": ["ppthdprod"],
        })
        kusto_result = MagicMock()
        kusto_result.to_df.return_value = kusto_df
        mock_kusto.query = AsyncMock(return_value=kusto_result)

        with patch(
            "zerotoil.tsgs.failover_pending_transaction.FailoverPendingTransaction._check_xfiles_partition_via_api",
            new_callable=AsyncMock,
            return_value=None,  # API failed
        ):
            tsg = _make_tsg()
            await tsg._run(_make_both_finalizefailover_input())

        assert tsg.mitigation_status == "Transferred"
        assert "Kusto" in tsg.xds_evidence_summary
        assert "SMB" in tsg.mitigation_detail

    @patch("zerotoil.tsgs.failover_pending_transaction.kusto")
    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_both_api_and_kusto_fail_human_fallback(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account, mock_kusto,
    ):
        """Both XDS API and Kusto fail → human fallback with full command."""
        _setup_dgrep_for_both_finalizefailover(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        mock_kusto.query = AsyncMock(side_effect=Exception("Kusto unavailable"))

        with patch(
            "zerotoil.tsgs.failover_pending_transaction.FailoverPendingTransaction._check_xfiles_partition_via_api",
            new_callable=AsyncMock,
            return_value=None,  # API failed
        ):
            tsg = _make_tsg()
            result = await tsg._run(_make_both_finalizefailover_input())

        assert result.mitigation_status == "ManualActionRequired"
        assert "Get-XdsPartition" in tsg.mitigation_detail
        assert "XDS API and Kusto" in tsg.xds_evidence_summary
        # Verify instructions were posted to ICM
        mock_incident.add_description.assert_called()
        desc_text = mock_incident.add_description.call_args[0][0]
        assert "Get-XdsPartition" in desc_text
        assert "MS-MEL23PrdStr11D" in desc_text


# ── Test: Branch D — Both sides at DnsSwitch ──────────────


def _make_both_dnsswitch_input(**overrides) -> FailoverPendingTransactionInput:
    """Build test input where both sides are at DnsSwitch."""
    defaults = dict(
        incident_id="770004255",
        tenant_name="RSRPAustraliaEast",
        incident_start_time_utc=datetime(2026, 3, 28, 15, 49, 9, 400000),
        environment="Public",
    )
    defaults.update(overrides)
    return FailoverPendingTransactionInput(**defaults)


def _setup_dgrep_for_both_dnsswitch(mock_dgrep):
    """Configure DGrep mocks so Step 3 returns both sides at DnsSwitch."""
    not_complete_df = pd.DataFrame({
        "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
        "accountName": ["ppthdprod"],
        "accountFailoverStatusType": ["InProgress"],
        "operationId": ["911d7400-323c-4858-a2c4-dae86475555c"],
    })
    stage_df = pd.DataFrame({
        "PreciseTimeStamp": ["2026-03-28T15:49:27.9807936Z"],
        "accountName": ["ppthdprod"],
        "PrimaryStage": ["DnsSwitch"],
        "SecondaryStage": ["DnsSwitch"],
    })
    mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
        step1_df=INCIDENT_770004255_STEP1_DF,
        step2_df=not_complete_df,
        step3_df=stage_df,
    ))


class TestBranchDDnsSwitch:
    """Test Branch D: both sides at DnsSwitch → search Secondary for 0x830a382d."""

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_error_code_found(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """0x830a382d found on Secondary XACServer → escalate to ximi."""
        _setup_dgrep_for_both_dnsswitch(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        xac_df = pd.DataFrame({
            "componentName": ["ms-mel23prdstr11d$xacserver_in_2"],
            "level": ["verbose"],
            "timestamp": ["2026-03-28 15:48:05.951280"],
            "message": ["DnsSwitch failed with error 0x830a382d for account ppthdprod"],
        })
        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(xac_df),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_dnsswitch_input())

        assert result.mitigation_status == "Escalated"
        assert ("ximi@microsoft.com" in tsg.mitigation_detail) or ("XGeo DRI" in tsg.mitigation_detail)
        assert tsg.mitigation_status == "Escalated"
        assert "0x830a382d" in tsg.xds_evidence_summary
        assert tsg.primary_stage == "DnsSwitch"
        assert tsg.secondary_stage == "DnsSwitch"

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_error_code_not_found(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """0x830a382d not found → default escalation."""
        _setup_dgrep_for_both_dnsswitch(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        empty_df = pd.DataFrame(columns=["componentName", "level", "timestamp", "message"])
        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(empty_df),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_dnsswitch_input())

        assert result.mitigation_status == "Escalated"
        assert tsg.mitigation_status == "Escalated"
        assert "no 0x830a382d" in tsg.xds_evidence_summary

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_searches_secondary_tenant(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """Branch D searches the Secondary (geo_pair) tenant."""
        _setup_dgrep_for_both_dnsswitch(mock_dgrep)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        empty_df = pd.DataFrame(columns=["componentName", "level", "timestamp", "message"])
        mock_xds.search_log = AsyncMock(
            return_value=_make_xds_result(empty_df),
        )
        mock_xds.generate_log_search_link = AsyncMock(
            return_value="https://fake-xds-link",
        )

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        result = await tsg._run(_make_both_dnsswitch_input())

        assert result.mitigation_status == "Escalated"
        # XDS search was called with geo-pair tenant (Secondary)
        search_call = mock_xds.search_log.call_args
        assert search_call[0][0] == "MS-MEL23PrdStr11D"


class TestExtractInputIncident770004255:
    """Test extraction for the real incident 770004255 title."""

    async def test_extracts_tenant_from_770004255(self):
        tsg = _make_tsg()
        incident = _make_incident_770004255()
        result = await tsg._extract_input_from_incident("770004255", incident)

        assert result.tenant_name == "RSRPAustraliaEast"
        assert result.environment == "Production"
        assert result.incident_start_time_utc == datetime(2026, 3, 28, 15, 49, 9, 400000)


# ── Dry-Run Mode Tests ──────────────────────────────────────


class TestDryRunMode:
    """Tests that dry_run=True skips all ICM write operations."""

    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_dry_run_completed_skips_mitigate(self, mock_dgrep, mock_icm):
        """Completed failover in dry-run should NOT call add_description or mitigate."""
        mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
            step1_df=INCIDENT_770004255_STEP1_DF,
            step2_df=INCIDENT_770004255_STEP2_COMPLETE_DF,
        ))

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.mitigate = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = FailoverPendingTransaction(dry_run=True)
        tsg.dgrep_links = []
        result = await tsg._run(_make_input_770004255())

        # Read operations still produce correct results
        assert result.is_completed
        assert result.account_name == "ppthdprod"

        # No ICM writes
        mock_icm.get_incident.assert_not_called()
        mock_incident.add_description.assert_not_called()
        mock_incident.mitigate.assert_not_called()

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_dry_run_escalation_no_write_no_raise(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account
    ):
        """Escalation path in dry-run should NOT write to ICM or raise ManualActionRequired."""
        mock_dgrep.query = AsyncMock(side_effect=_make_dgrep_query_side_effect(
            step1_df=STEP1_ALERT_DF,
            step2_df=pd.DataFrame(columns=["OperationId", "AccountName", "IsSuccess"]),
            step3_df=pd.DataFrame(columns=[
                "PreciseTimeStamp", "PrimaryStage", "SecondaryStage",
                "PrimaryGeoConfigOff", "SecondaryGeoConfigOff",
            ]),
        ))

        mock_xds.log_search = AsyncMock(
            return_value=_make_xds_result(pd.DataFrame(columns=["message", "PreciseTimeStamp"]))
        )

        account_obj = MagicMock()
        account_obj.primary_stamp = "MS-XYZ01PrdStr01A"
        account_obj.secondary_stamp = "MS-ABC02PrdStr02A"
        mock_get_account.return_value = account_obj

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_incident.transfer = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = FailoverPendingTransaction(dry_run=True)
        tsg.dgrep_links = []
        inp = _make_input(
            tenant_name="RSRPWestUS",
            expected_stuck_location="Secondary",
            expected_stuck_stage="PrepareFailover",
        )

        # Should NOT raise ManualActionRequired in dry-run
        result = await tsg._run(inp)

        # No ICM writes
        mock_incident.add_description.assert_not_called()
        mock_incident.transfer.assert_not_called()
        mock_incident.mitigate.assert_not_called()

    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_dry_run_flag_propagates(self, mock_dgrep, mock_icm):
        """Verify dry_run=True is set on the instance."""
        tsg = FailoverPendingTransaction(dry_run=True)
        assert tsg.dry_run is True

        tsg2 = FailoverPendingTransaction()
        assert tsg2.dry_run is False

        tsg3 = FailoverPendingTransaction(dry_run=False)
        assert tsg3.dry_run is False


# ── Test: Step 3 fallback from matched_stuck ───────────────


@pytest.mark.asyncio
class TestStep3FallbackFromMatchedStuck:
    """Test that Step 3 uses matched_stuck when DGrep returns no data."""

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_fallback_secondary_prepare_failover(self, mock_dgrep):
        """matched_stuck='SecondaryStuck.PrepareFailover' → sets secondary side."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        tsg.account_name = "testaccount"
        tsg.matched_stuck = "SecondaryStuck.PrepareFailover"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Secondary"
        assert tsg.stuck_stage == "PrepareFailover"
        assert tsg.secondary_stage == "PrepareFailover"
        assert tsg.primary_stage == ""
        assert tsg.stage_source == "matched_stuck"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_fallback_primary_prepare_failover(self, mock_dgrep):
        """matched_stuck='PrimaryStuck.PrepareFailover' → sets primary side."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        tsg.account_name = "testaccount"
        tsg.matched_stuck = "PrimaryStuck.PrepareFailover"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Primary"
        assert tsg.stuck_stage == "PrepareFailover"
        assert tsg.primary_stage == "PrepareFailover"
        assert tsg.secondary_stage == ""
        assert tsg.stage_source == "matched_stuck"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_fallback_secondary_soft_finalize(self, mock_dgrep):
        """matched_stuck='SecondaryStuck.SoftFinalizeFailover' → sets secondary."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        tsg.account_name = "testaccount"
        tsg.matched_stuck = "SecondaryStuck.SoftFinalizeFailover"
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Secondary"
        assert tsg.stuck_stage == "SoftFinalizeFailover"
        assert tsg.secondary_stage == "SoftFinalizeFailover"
        assert tsg.stage_source == "matched_stuck"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_fallback_to_incident_title(self, mock_dgrep):
        """No matched_stuck but expected_stuck in input → fallback to title."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        tsg.account_name = "testaccount"
        tsg.matched_stuck = ""  # No matched_stuck
        inp = _make_input(
            expected_stuck_location="Secondary",
            expected_stuck_stage="HardFinalizeFailover",
        )
        await tsg._step_3_determine_stuck_stage(inp)

        assert tsg.stuck_location == "Secondary"
        assert tsg.stuck_stage == "HardFinalizeFailover"
        assert tsg.secondary_stage == "HardFinalizeFailover"
        assert tsg.stage_source == "incident_title"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_unknown_when_all_fallbacks_fail(self, mock_dgrep):
        """No DGrep data, no matched_stuck, no title info → Unknown."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(empty_df),
        )

        tsg = _make_tsg()
        tsg.account_name = "testaccount"
        tsg.matched_stuck = ""
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stuck_location == "Unknown"
        assert tsg.stuck_stage == "Unknown"

    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_statistics_event_takes_priority(self, mock_dgrep):
        """When DGrep has data, matched_stuck fallback is NOT used."""
        df = pd.DataFrame({
            "PreciseTimeStamp": [datetime(2026, 3, 20, 23, 0)],
            "accountName": ["testaccount"],
            "PrimaryStage": ["FinalizeFailover"],
            "SecondaryStage": ["PrepareFailover"],
        })
        mock_dgrep.query = AsyncMock(
            return_value=_make_dgrep_result(df),
        )

        tsg = _make_tsg()
        tsg.account_name = "testaccount"
        tsg.matched_stuck = "SecondaryStuck.DnsSwitch"  # Different from DGrep
        await tsg._step_3_determine_stuck_stage(_make_input())

        assert tsg.stage_source == "statistics_event"
        assert tsg.primary_stage == "FinalizeFailover"
        assert tsg.secondary_stage == "PrepareFailover"
        assert tsg.stuck_location == "Secondary"


# ── Test: Single-side routing in Step 4 ──────────────────────


@pytest.mark.asyncio
class TestSingleSideRouting:
    """Test Step 4 routing when only one side's stage is known."""

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_single_side_prepare_failover_routes_branch_a(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """Single-side PrepareFailover → Branch A, searches both tenants."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        # Step 1 returns alert data with operation/account AND stuck label
        step1_df = pd.DataFrame({
            "PreciseTimeStamp": [
                datetime(2026, 4, 26, 18, 0),
                datetime(2026, 4, 26, 18, 0),
            ],
            "Message": [
                "[AccountFailover] [PendingFailoverOperation] "
                "[OperationId: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee, "
                "account name: testacctFailoverType: Hard, "
                "StartTimeInUtc: 4/26/2026 5:42:35 PM] "
                "Failover has been flagged and alerted for SLA breach.",
                "[metric:FailoverTransactionSLABreachMetric. "
                "dimensionValues: SecondaryStuck.PrepareFailover",
            ],
            "ActivityId": [
                "11111111-2222-3333-4444-555555555555",
                "11111111-2222-3333-4444-555555555555",
            ],
        })

        def dgrep_side_effect(**kwargs):
            event = kwargs.get("event_names", "")
            if "ServiceBackgroundActivity" in event:
                return _make_dgrep_result(step1_df)
            return _make_dgrep_result(empty_df)

        mock_dgrep.query = AsyncMock(side_effect=dgrep_side_effect)
        mock_get_account.return_value = _make_account_entity(
            tenant_name="MS-SYD24PrdStr02A",
            geo_pair_name="MS-MEL23PrdStr11D",
        )

        mock_xds.search_log = AsyncMock(return_value=_make_xds_result(pd.DataFrame()))
        mock_xds.generate_log_search_link = AsyncMock(return_value="https://fake-link")

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = _make_tsg()
        inp = _make_input(
            tenant_name="RSRPPublicPreprodEastUS2",
            expected_stuck_location="Secondary",
            expected_stuck_stage="PrepareFailover",
        )

        result = await tsg._run(inp)

        assert result.mitigation_status == "Escalated"
        # Should have searched XDS on BOTH tenants (primary + geo-pair)
        search_calls = mock_xds.search_log.call_args_list
        searched_tenants = {call[0][0] for call in search_calls}
        assert "MS-SYD24PrdStr02A" in searched_tenants
        assert "MS-MEL23PrdStr11D" in searched_tenants
        assert tsg.stage_source == "matched_stuck"

    @patch("zerotoil.tsgs.failover_pending_transaction.get_account")
    @patch("zerotoil.tsgs.failover_pending_transaction.icm")
    @patch("zerotoil.tsgs.failover_pending_transaction.xds")
    @patch("zerotoil.tsgs.failover_pending_transaction.dgrep")
    async def test_single_side_soft_finalize_routes_branch_c(
        self, mock_dgrep, mock_xds, mock_icm, mock_get_account,
    ):
        """Single-side SoftFinalizeFailover → Branch C (FinalizeFailover logic)."""
        empty_df = pd.DataFrame(
            columns=["PreciseTimeStamp", "accountName", "PrimaryStage", "SecondaryStage"],
        )
        step1_df = pd.DataFrame({
            "PreciseTimeStamp": [
                datetime(2026, 4, 26, 18, 0),
                datetime(2026, 4, 26, 18, 0),
            ],
            "Message": [
                "[AccountFailover] [PendingFailoverOperation] "
                "[OperationId: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee, "
                "account name: testacctFailoverType: Hard, "
                "StartTimeInUtc: 4/26/2026 5:42:35 PM] "
                "Failover has been flagged and alerted for SLA breach.",
                "[metric:FailoverTransactionSLABreachMetric. "
                "dimensionValues: SecondaryStuck.SoftFinalizeFailover",
            ],
            "ActivityId": [
                "11111111-2222-3333-4444-555555555555",
                "11111111-2222-3333-4444-555555555555",
            ],
        })

        def dgrep_side_effect(**kwargs):
            event = kwargs.get("event_names", "")
            if "ServiceBackgroundActivity" in event:
                return _make_dgrep_result(step1_df)
            return _make_dgrep_result(empty_df)

        mock_dgrep.query = AsyncMock(side_effect=dgrep_side_effect)
        mock_get_account.return_value = _make_account_entity()

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        # Mock the XFiles partition check method (Branch C internals)
        with patch(
            "zerotoil.tsgs.failover_pending_transaction.FailoverPendingTransaction._check_xfiles_partition_via_api",
            new_callable=AsyncMock,
            return_value=None,  # API failed → will escalate
        ), patch(
            "zerotoil.tsgs.failover_pending_transaction.kusto",
        ) as mock_kusto:
            mock_kusto.query = AsyncMock(side_effect=Exception("Kusto unavailable"))

            tsg = _make_tsg()
            inp = _make_input(
                tenant_name="RSRPPublicPreprodEastUS2",
                expected_stuck_location="Secondary",
                expected_stuck_stage="SoftFinalizeFailover",
            )
            result = await tsg._run(inp)

        assert result.mitigation_status == "ManualActionRequired"
        assert "Get-XdsPartition" in tsg.mitigation_detail
        assert tsg.stage_source == "matched_stuck"
        assert tsg.stuck_stage == "SoftFinalizeFailover"


# ── Test: _FINALIZE_STAGES constant ──────────────────────────


class TestFinalizeStages:
    """Verify the _FINALIZE_STAGES set."""

    def test_contains_all_finalize_variants(self):
        assert "finalizefailover" in _FINALIZE_STAGES
        assert "softfinalizefailover" in _FINALIZE_STAGES
        assert "hardfinalizefailover" in _FINALIZE_STAGES

    def test_does_not_contain_other_stages(self):
        assert "preparefailover" not in _FINALIZE_STAGES
        assert "dnsswitch" not in _FINALIZE_STAGES


# ── Test: Stage index for new stages ─────────────────────────


class TestStageIndexNewStages:
    """Verify the new SoftFinalizeFailover and HardFinalizeFailover stages."""

    def test_soft_finalize_after_finalize(self):
        assert _stage_index("SoftFinalizeFailover") > _stage_index("FinalizeFailover")

    def test_hard_finalize_after_soft(self):
        assert _stage_index("HardFinalizeFailover") > _stage_index("SoftFinalizeFailover")

    def test_poll_finalize_after_hard(self):
        assert _stage_index("PollFinalizeFailover") > _stage_index("HardFinalizeFailover")

    def test_case_insensitive_soft_finalize(self):
        assert _stage_index("softfinalizefailover") == _stage_index("SoftFinalizeFailover")

    def test_case_insensitive_hard_finalize(self):
        assert _stage_index("hardfinalizefailover") == _stage_index("HardFinalizeFailover")




class TestSelectEscalationTarget:
    """Cover the timezone-aware escalation routing helper."""

    def test_china_working_hours_routes_to_ximi(self):
        from datetime import datetime, timezone
        # 2026-05-06 12:00 Asia/Shanghai (UTC+8) → 04:00 UTC, weekday=Tue.
        now = datetime(2026, 5, 6, 4, 0, tzinfo=timezone.utc)
        target, route, key = FailoverPendingTransaction._select_escalation_target(now)
        assert key == "ximi"
        assert "ximi@microsoft.com" in target
        assert "China" in route

    def test_china_after_hours_routes_to_xgeo(self):
        from datetime import datetime, timezone
        # 2026-05-06 22:00 Asia/Shanghai → 14:00 UTC. After 18:00 CN.
        now = datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc)
        target, route, key = FailoverPendingTransaction._select_escalation_target(now)
        assert key == "xgeo"
        assert "XGeo DRI" in target

    def test_weekend_routes_to_xgeo(self):
        from datetime import datetime, timezone
        # 2026-05-09 12:00 Asia/Shanghai is Saturday → not CN business day.
        now = datetime(2026, 5, 9, 4, 0, tzinfo=timezone.utc)
        target, route, key = FailoverPendingTransaction._select_escalation_target(now)
        assert key == "xgeo"
