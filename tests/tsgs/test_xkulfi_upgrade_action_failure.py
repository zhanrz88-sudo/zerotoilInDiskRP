"""Unit tests for XKulfiUpgradeActionFailure TSG — Step 1 + Step 2.

Drives the parser against the 40 real titles captured in
``zero-toil/tsgs/xkulfi-upgrade-action-failure/SampleIncidents.md`` plus a
handful of targeted edge-case assertions; also covers Step 2's DGrep
query construction and result mapping (mocked).

Run:
    cd zero-toil
    pytest tests/tsgs/test_xkulfi_upgrade_action_failure.py -v
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from zerotoil.tsgs.xkulfi_upgrade_action_failure import (
    XKulfiUpgradeActionFailure,
    XKulfiUpgradeActionFailureInput,
)


# ── Helpers ──────────────────────────────────────────────────


_SAMPLE_INCIDENTS_MD = (
    Path(__file__).resolve().parents[2]
    / "tsgs"
    / "xkulfi-upgrade-action-failure"
    / "SampleIncidents.md"
)


def _load_sample_titles() -> list[str]:
    """Return the raw titles between the SAMPLE_INCIDENTS markers."""
    text = _SAMPLE_INCIDENTS_MD.read_text(encoding="utf-8")
    m = re.search(
        r"<!-- BEGIN: RAW_TITLES -->(.*?)<!-- END: RAW_TITLES -->",
        text,
        re.S,
    )
    assert m, "RAW_TITLES block not found in SampleIncidents.md"
    return [
        line for line in m.group(1).splitlines()
        if line.strip().startswith("[XKulfi]")
    ]


SAMPLE_TITLES = _load_sample_titles()
assert len(SAMPLE_TITLES) >= 40, (
    f"Expected ≥40 sample titles, got {len(SAMPLE_TITLES)} — "
    "check SampleIncidents.md RAW_TITLES block."
)


def _make_incident(
    title: str,
    *,
    create_date: datetime | None = None,
    descriptions: list | None = None,
) -> MagicMock:
    incident = MagicMock()
    incident.Title = title
    incident.CreateDate = create_date or datetime(2026, 4, 28, 12, 0, 0)
    incident.Descriptions = descriptions or []
    return incident


def _make_tsg() -> XKulfiUpgradeActionFailure:
    tsg = XKulfiUpgradeActionFailure(dry_run=True)
    # Reset class-level mutable defaults on this instance so tests don't
    # share state across the module's class-level `failure_logs = []`.
    tsg.failure_logs = []
    return tsg


def _make_input(incident_id: str = "12345") -> XKulfiUpgradeActionFailureInput:
    return XKulfiUpgradeActionFailureInput(incident_id=incident_id)


async def _parse(title: str, **incident_kwargs) -> XKulfiUpgradeActionFailure:
    """Run step_1_parse_incident against ``title`` and return the TSG."""
    tsg = _make_tsg()
    incident = _make_incident(title, **incident_kwargs)
    with patch(
        "zerotoil.tsgs.xkulfi_upgrade_action_failure.icm",
    ) as mock_icm:
        mock_icm.get_incident = AsyncMock(return_value=incident)
        await tsg.step_1_parse_incident(_make_input())
    return tsg


# ── All-samples sweep ───────────────────────────────────────


class TestAllSampleIncidents:
    """Parametrized sweep across every title in SampleIncidents.md.

    Every modern XKulfi UpgradeActionFailure title carries the canonical
    ``[Tenant=]``, ``[OperationName=]``, ``[RepairKind=]`` tokens — so the
    parser must populate those three for every sample.
    """

    @pytest.mark.parametrize(
        "idx,title",
        list(enumerate(SAMPLE_TITLES, start=1)),
        ids=[f"row{i}" for i in range(1, len(SAMPLE_TITLES) + 1)],
    )
    async def test_canonical_tokens_populated(self, idx: int, title: str):
        tsg = await _parse(title)
        assert tsg.tenant, f"row {idx}: tenant empty for title {title!r}"
        assert tsg.operation, f"row {idx}: operation empty for title {title!r}"
        assert tsg.rollout_type, f"row {idx}: rollout_type empty for title {title!r}"
        # Version is in [Version=...] for every modern title.
        assert tsg.target_version, (
            f"row {idx}: target_version empty for title {title!r}"
        )

    async def test_tenant_always_matches_tenant_token_not_title_prefix(self):
        """Tenant must come from ``[Tenant=...]`` — never the title prefix.

        Several rows in SampleIncidents.md have a title-prefix cluster name
        that differs from the actual tenant inside ``[Tenant=...]``
        (e.g. row 19 prefix ``MS-BLZ04PrdStez100A`` vs tenant
        ``MS-MNZ09PrdSte100A``). Verify the parser picks the latter for
        every sample.
        """
        token_re = re.compile(r"\[Tenant=([^\]]+)\]")
        for idx, title in enumerate(SAMPLE_TITLES, start=1):
            m = token_re.search(title)
            assert m, f"row {idx}: no [Tenant=...] token in title"
            expected_tenant = m.group(1).strip()
            tsg = await _parse(title)
            assert tsg.tenant == expected_tenant, (
                f"row {idx}: tenant {tsg.tenant!r} != [Tenant=] token "
                f"{expected_tenant!r}"
            )


# ── Targeted shape coverage ─────────────────────────────────


class TestActionKeyShapes:
    """One assertion per observed ActionKey shape."""

    async def test_shape_a_bracketed_with_upgrade_domain(self):
        # SampleIncidents.md row 2 — OSUpgrade, per-domain bracketed ActionKey.
        tsg = await _parse(SAMPLE_TITLES[1])
        assert tsg.operation == "MonitorUpgradeBatchProgressOperation"
        assert tsg.tenant == "MS-SYD27PrdStp06A"
        assert tsg.rollout_type == "OSUpgrade"
        assert tsg.target_version == "26.02.06W2022.XSTORE"
        assert tsg.domain == "6"
        # OSUpgrade puts the build version in the deployment_id slot.
        assert tsg.deployment_id == "26.02.06W2022.XSTORE"
        assert tsg.app == "MaintenanceService2"

    async def test_shape_b_bracketed_without_upgrade_domain(self):
        # SampleIncidents.md row 39 — bracketed ActionKey lacks UpgradeDomain.
        tsg = await _parse(SAMPLE_TITLES[38])
        assert tsg.operation == "SmokeTestOperation"
        assert tsg.tenant == "MS-CVL01PrdStf01A"
        assert tsg.rollout_type == "AppRollout"
        assert tsg.deployment_id == "01DCCD730C60AED1:5717"
        assert tsg.target_version == "RELEASE_STG104_224/104.467.224.400"
        assert tsg.app == "APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE"
        # No [UpgradeDomain=] token AND no UpgradeDomain segment in ActionKey
        # — domain must be None (not, e.g., a stray "0").
        assert tsg.domain is None

    async def test_shape_c_flat_semicolon_deployment_level(self):
        # SampleIncidents.md row 1 — ValidateBuildOperation, flat C ActionKey.
        tsg = await _parse(SAMPLE_TITLES[0])
        assert tsg.operation == "ValidateBuildOperation"
        assert tsg.tenant == "MS-CDM40PrdSty02A"
        assert tsg.rollout_type == "AppRollout"
        assert tsg.deployment_id == "01DCCB8A7C608163:3160"
        assert tsg.app == "APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE"
        assert tsg.target_version == "UnknownSTGVersion"
        assert tsg.domain is None

    async def test_shape_d_flat_semicolon_check_left_over(self):
        # SampleIncidents.md row 20 — CheckLeftOverMachinesBeforeUnbookOperation.
        tsg = await _parse(SAMPLE_TITLES[19])
        assert tsg.operation == "CheckLeftOverMachinesBeforeUnbookOperation"
        assert tsg.tenant == "MS-AMS26PrdStr14B"
        assert tsg.rollout_type == "AppRollout"
        assert tsg.deployment_id == "01DCB8DABC81090C:26851"
        assert tsg.app == "APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE"
        # Shape D has no version inside the ActionKey — the [Version=] token
        # provides it.
        assert tsg.target_version == "RELEASE_STG103_468/103.334.468.1000"


# ── Edge cases ──────────────────────────────────────────────


class TestTitleParseEdgeCases:

    async def test_title_prefix_cluster_differs_from_tenant_token(self):
        # SampleIncidents.md row 19 — prefix ``MS-BLZ04PrdStez100A`` vs
        # tenant ``MS-MNZ09PrdSte100A``.
        tsg = await _parse(SAMPLE_TITLES[18])
        assert tsg.tenant == "MS-MNZ09PrdSte100A"
        assert "MS-BLZ04" not in tsg.tenant

    async def test_truncated_title_degrades_gracefully(self):
        # SampleIncidents.md row 37 — title is truncated mid-ActionKey
        # (unbalanced brackets). All [Tenant=]/[OperationName=]/[RepairKind=]/
        # [Version=] tokens precede the cut, so they must still parse.
        tsg = await _parse(SAMPLE_TITLES[36])
        assert tsg.operation == "CheckRolePingBeforeUnprepareOperation"
        assert tsg.tenant == "MS-PHX25PrdStr38A"
        assert tsg.rollout_type == "FeatureFlagsUpgrade"
        assert tsg.target_version.startswith("DotNetCore_")
        # ActionKey is truncated → deployment_id / app cannot be recovered.
        assert tsg.deployment_id == ""
        assert tsg.app is None

    async def test_shared_action_key_routes_per_operation(self):
        # SampleIncidents.md rows 31–34 share an ActionKey and only differ
        # by OperationName. Verify the parser picks the OperationName token,
        # not whatever happens to appear first.
        expected_ops = [
            "UpdateConfigurationStorageVersionOperation",
            "ScheduleXComputeJobsOperation",
            "UpdateStgVersionOperation",
            "ResetWatchdogConfigOperation",
        ]
        for offset, expected_op in enumerate(expected_ops):
            tsg = await _parse(SAMPLE_TITLES[30 + offset])
            assert tsg.operation == expected_op
            # All four are the same DSM14 deployment.
            assert tsg.tenant == "MS-DSM14PrdSte28A"
            assert tsg.deployment_id == "01DCC2C1CFF3B717:1911"

    async def test_rerun_resets_state(self):
        """Calling step_1_parse_incident twice must not carry stale state."""
        tsg = _make_tsg()
        # Seed stale values from a previous invocation.
        tsg.tenant = "OLD-TENANT"
        tsg.operation = "OldOperation"
        tsg.domain = "9"
        tsg.app = "APP~OLD"
        tsg.deployment_id = "OLD:1"
        # Row 1 has no UpgradeDomain — domain must reset to None.
        with patch(
            "zerotoil.tsgs.xkulfi_upgrade_action_failure.icm",
        ) as mock_icm:
            mock_icm.get_incident = AsyncMock(
                return_value=_make_incident(SAMPLE_TITLES[0]),
            )
            await tsg.step_1_parse_incident(_make_input())
        assert tsg.tenant == "MS-CDM40PrdSty02A"
        assert tsg.operation == "ValidateBuildOperation"
        assert tsg.domain is None
        assert tsg.app == "APP~CEG_AZURESTORAGE-XSTORE-GLOBAL-VE"

    async def test_description_fallback_when_title_lacks_tokens(self):
        """If the title is empty but a description carries the canonical
        tokens, the parser must recover from the description body."""
        # Strip everything after the first "Alert:" so the title has no tokens.
        bare_title = "[XKulfi] [East US] [XStore] MS-IAD04PrdStp02A Alert"
        full_payload = SAMPLE_TITLES[4]  # row 5 — has all tokens + ActionKey
        desc = MagicMock()
        desc.Text = full_payload
        tsg = await _parse(bare_title, descriptions=[desc])
        assert tsg.operation == "CheckRolePingBeforeUnprepareOperation"
        assert tsg.tenant == "MS-IAD04PrdStp02A"
        assert tsg.rollout_type == "OSUpgrade"
        assert tsg.deployment_id == "26.03.27W2022.XSTORE"
        assert tsg.domain == "6"

    async def test_unparseable_title_yields_empty_operation(self):
        """A title with no XKulfi tokens at all must not raise; it should
        leave ``operation`` empty so Step 3 routes to the generic branch."""
        tsg = await _parse("Some unrelated incident title")
        assert tsg.operation == ""
        assert tsg.tenant == ""
        assert tsg.rollout_type == ""
        assert tsg.deployment_id == ""
        assert tsg.domain is None

    async def test_incident_metadata_recorded(self):
        """``incident_title`` and ``incident_create_date`` are set so Step 2
        can anchor its DGrep query window."""
        create_date = datetime(2026, 4, 28, 8, 50, 45)
        tsg = await _parse(SAMPLE_TITLES[9], create_date=create_date)
        assert tsg.incident_title == SAMPLE_TITLES[9]
        assert tsg.incident_create_date == create_date


# ── dgrep_tenant extraction (per step-1-parse-incident.md §4) ──


class TestDgrepTenantExtraction:
    """The DGrep tenant is surfaced in the incident description as a key
    like ``Icm.RaisingLocation\\tXKulfiEastUS-Prod-BL2P``. It is distinct
    from the rollout tenant and must be parsed for Step 2's DGrep scope.
    """

    async def test_extracts_dgrep_tenant_from_tab_separated_description(self):
        desc = MagicMock()
        desc.Text = "Icm.RaisingLocation\tXKulfiEastUS-Prod-BL2P\nOther.Field\tvalue"
        tsg = await _parse(SAMPLE_TITLES[4], descriptions=[desc])
        assert tsg.dgrep_tenant == "XKulfiEastUS-Prod-BL2P"
        # Rollout tenant must be unchanged.
        assert tsg.tenant == "MS-IAD04PrdStp02A"

    async def test_extracts_dgrep_tenant_from_html_table_description(self):
        # ICM rendered descriptions are typically HTML tables — verify the
        # liberal separator regex handles closing/opening tags between key
        # and value.
        desc = MagicMock()
        desc.Text = (
            "<tr><td>Icm.RaisingLocation</td><td>XKulfiAustraliaEast-Prod-SY3P"
            "</td></tr>"
        )
        tsg = await _parse(SAMPLE_TITLES[1], descriptions=[desc])
        assert tsg.dgrep_tenant == "XKulfiAustraliaEast-Prod-SY3P"

    async def test_dgrep_tenant_none_when_description_missing(self):
        tsg = await _parse(SAMPLE_TITLES[0])  # no descriptions
        assert tsg.dgrep_tenant is None

    async def test_dgrep_tenant_none_when_description_lacks_key(self):
        desc = MagicMock()
        desc.Text = "Some unrelated description body without the key."
        tsg = await _parse(SAMPLE_TITLES[0], descriptions=[desc])
        assert tsg.dgrep_tenant is None

    async def test_dgrep_tenant_first_match_wins_across_descriptions(self):
        d1 = MagicMock()
        d1.Text = "no key here"
        d2 = MagicMock()
        d2.Text = "Icm.RaisingLocation\tXKulfiNorthEurope-Prod-DB3P"
        d3 = MagicMock()
        d3.Text = "Icm.RaisingLocation\tShouldNotWin"
        tsg = await _parse(SAMPLE_TITLES[3], descriptions=[d1, d2, d3])
        assert tsg.dgrep_tenant == "XKulfiNorthEurope-Prod-DB3P"

    async def test_rerun_resets_dgrep_tenant(self):
        """A second invocation with no description must clear a stale
        ``dgrep_tenant`` from a previous run."""
        tsg = _make_tsg()
        tsg.dgrep_tenant = "OLD-DGREP-TENANT"
        with patch(
            "zerotoil.tsgs.xkulfi_upgrade_action_failure.icm",
        ) as mock_icm:
            mock_icm.get_incident = AsyncMock(
                return_value=_make_incident(SAMPLE_TITLES[0]),
            )
            await tsg.step_1_parse_incident(_make_input())
        assert tsg.dgrep_tenant is None


# ── alert_keyword extraction (per step-1-parse-incident.md §4) ──


# Real description fragment from incident 783567635 — captures the canonical
# "Alert keyword: <kw> result:" shape that Step 2 relies on.
_REAL_ALERT_KEYWORD = (
    "Upgrade action SmokeTestOperation for "
    "[[XKulfi]MS-BLZ21PrdStr27A-ApServiceRollout-01DCD0F8AF50EDDD:14277]"
    "[APP~AUTOPILOT-AUTOPILOTCLIENT-VE][AP_2026_04_06_5003]"
    "[UpgradeDomain=7][2026-04-21T10:31:42Z]"
)


class TestAlertKeywordExtraction:
    """The alert keyword is surfaced in the description Message field as
    ``Alert keyword: <kw> result:``. It is the exact string Step 2 plugs
    into ``message.contains(...)`` to pin the DGrep query to this incident.
    """

    async def test_extracts_alert_keyword_from_real_description_shape(self):
        # Real incident 783567635 — the value before " result:" must be
        # captured verbatim, including all bracketed segments.
        body = (
            f"Message Environment: PROD; Region: East US; "
            f"XKulfi tenant: XKulfiEastUS-Prod-BL2P; "
            f"Alert keyword: {_REAL_ALERT_KEYWORD} result:;"
        )
        desc = MagicMock()
        desc.Text = body
        tsg = await _parse(SAMPLE_TITLES[4], descriptions=[desc])
        assert tsg.alert_keyword == _REAL_ALERT_KEYWORD

    async def test_extracts_alert_keyword_terminated_by_semicolon(self):
        # When ``result:`` is missing, ``;`` is the next-best terminator.
        desc = MagicMock()
        desc.Text = "Alert keyword: Upgrade action FooOp for [thing]; next field"
        tsg = await _parse(SAMPLE_TITLES[0], descriptions=[desc])
        assert tsg.alert_keyword == "Upgrade action FooOp for [thing]"

    async def test_extracts_alert_keyword_terminated_by_html_tag(self):
        # Rendered ICM HTML wraps the field — the value stops at the first
        # ``<`` (start of the closing tag).
        desc = MagicMock()
        desc.Text = "<td>Alert keyword: Upgrade action BarOp for [thing] result:</td>"
        tsg = await _parse(SAMPLE_TITLES[0], descriptions=[desc])
        assert tsg.alert_keyword == "Upgrade action BarOp for [thing]"

    async def test_alert_keyword_none_when_description_missing(self):
        tsg = await _parse(SAMPLE_TITLES[0])
        assert tsg.alert_keyword is None

    async def test_alert_keyword_none_when_description_lacks_key(self):
        desc = MagicMock()
        desc.Text = "Some unrelated description without the alert keyword field."
        tsg = await _parse(SAMPLE_TITLES[0], descriptions=[desc])
        assert tsg.alert_keyword is None

    async def test_alert_keyword_first_match_wins_across_descriptions(self):
        d1 = MagicMock()
        d1.Text = "no key here"
        d2 = MagicMock()
        d2.Text = "Alert keyword: First wins result:"
        d3 = MagicMock()
        d3.Text = "Alert keyword: Should not win result:"
        tsg = await _parse(SAMPLE_TITLES[0], descriptions=[d1, d2, d3])
        assert tsg.alert_keyword == "First wins"

    async def test_rerun_resets_alert_keyword(self):
        tsg = _make_tsg()
        tsg.alert_keyword = "STALE"
        with patch(
            "zerotoil.tsgs.xkulfi_upgrade_action_failure.icm",
        ) as mock_icm:
            mock_icm.get_incident = AsyncMock(
                return_value=_make_incident(SAMPLE_TITLES[0]),
            )
            await tsg.step_1_parse_incident(_make_input())
        assert tsg.alert_keyword is None


# ── Step 2 — fetch failure logs ─────────────────────────────


def _make_dgrep_result(df: pd.DataFrame, link: str = "https://fake-dgrep-link") -> MagicMock:
    """Create a mock ``dgrep.query`` result — mirrors the production shape."""
    result = MagicMock()
    result.to_df.return_value = df
    result.get_dgrep_link.return_value = link
    return result


def _make_step2_tsg(
    *,
    dgrep_tenant: str | None = "XKulfiEastUS-Prod-BL2P",
    alert_keyword: str | None = _REAL_ALERT_KEYWORD,
    rollout_tenant: str = "MS-BLZ21PrdStr27A",
    create_date: datetime | None = None,
) -> XKulfiUpgradeActionFailure:
    """Build a TSG with Step 1 outputs already populated, ready for Step 2."""
    tsg = _make_tsg()
    tsg.tenant = rollout_tenant
    tsg.dgrep_tenant = dgrep_tenant
    tsg.alert_keyword = alert_keyword
    tsg.incident_create_date = create_date or datetime(
        2026, 4, 21, 12, 19, 1, tzinfo=timezone.utc,
    )
    return tsg


class TestStep2DgrepQueryConstruction:
    """Verifies Step 2 issues exactly the query shape required by
    step-2-fetch-failure-logs.md (XKulfiTelemetry / TraceTelemetry,
    scope = {Tenant, Role: XKulfi}, message.contains("<keyword> result:")).
    """

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_query_uses_canonical_namespace_event_and_scope(
        self, mock_query, mock_dgrep,
    ):
        df = pd.DataFrame(
            [
                {
                    "PreciseTimeStamp": "2026-04-21T12:48:53Z",
                    "Message": "msg-1",
                    "RoleInstance": "BL2PEPF0001A2CB",
                    "STG_TenantName": "MS-BLZ21PrdStr27A",
                    "STG_VirtualTenantName": "MS-BLZ21PrdStrz27A",
                    "STG_PFEnvironment": "BLZ21PrdStr27A-Prod-IAD13P",
                    "Tenant": "XKulfiEastUS-Prod-BL2P",
                }
            ]
        )
        mock_query.return_value = _make_dgrep_result(df)
        mock_dgrep.get_dgrep_link.return_value = "https://prebuilt-dgrep-link"

        tsg = _make_step2_tsg()
        await tsg.step_2_fetch_failure_logs(_make_input())

        # The retry helper is what actually executes the query — inspect the
        # arguments it received.
        assert mock_query.call_count == 1
        _, kwargs = mock_query.call_args
        assert kwargs["namespaces"] == "XKulfiTelemetry"
        assert kwargs["event_names"] == "TraceTelemetry"
        assert kwargs["server_query_type"] == "MQL"
        assert kwargs["environment"] == "Production"
        assert kwargs["scope_conditions"] == {
            "Tenant": "XKulfiEastUS-Prod-BL2P",
            "Role": "XKulfi",
        }

        # Server query must contain the literal alert keyword.
        sq = kwargs["server_query"]
        assert f'message.contains("{_REAL_ALERT_KEYWORD}")' in sq
        # The legacy ' result:' suffix must NOT be appended.
        assert "result:" not in sq
        # Required select columns.
        for col in (
            "STG_TenantName",
            "STG_VirtualTenantName",
            "STG_PFEnvironment",
            "message",
            "PreciseTimeStamp",
            "RoleInstance",
            "Tenant",
        ):
            assert col in sq

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_query_window_is_anchored_to_incident_create_date(
        self, mock_query, mock_dgrep,
    ):
        anchor = datetime(2026, 4, 21, 12, 19, 1, tzinfo=timezone.utc)
        mock_query.return_value = _make_dgrep_result(pd.DataFrame())
        mock_dgrep.get_dgrep_link.return_value = ""

        tsg = _make_step2_tsg(create_date=anchor)
        # Default time_window_hours is 6.
        await tsg.step_2_fetch_failure_logs(_make_input())

        _, kwargs = mock_query.call_args
        assert kwargs["from_time"] == anchor - timedelta(hours=6)
        assert kwargs["to_time"] == anchor + timedelta(minutes=30)

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_dgrep_link_emitted_before_query_runs(
        self, mock_query, mock_dgrep,
    ):
        """Operators need the portal URL even when the query fails on
        permissions — Step 2 must build the link via ``dgrep.get_dgrep_link``
        before executing the query.
        """
        mock_dgrep.get_dgrep_link.return_value = "https://prebuilt-dgrep-link"
        mock_query.side_effect = RuntimeError("permission denied")

        tsg = _make_step2_tsg()
        await tsg.step_2_fetch_failure_logs(_make_input())

        # Link was built up-front and survived the query failure.
        assert mock_dgrep.get_dgrep_link.called
        assert tsg.dgrep_link == "https://prebuilt-dgrep-link"
        # No rows captured because the query raised.
        assert tsg.failure_logs == []

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_post_query_link_overrides_prebuilt_link(
        self, mock_query, mock_dgrep,
    ):
        mock_dgrep.get_dgrep_link.return_value = "https://prebuilt-link"
        mock_query.return_value = _make_dgrep_result(
            pd.DataFrame([{"PreciseTimeStamp": "t", "Message": "m"}]),
            link="https://post-query-link",
        )
        tsg = _make_step2_tsg()
        await tsg.step_2_fetch_failure_logs(_make_input())
        assert tsg.dgrep_link == "https://post-query-link"


class TestStep2RowMappingAndBehavior:

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_rows_capture_all_select_columns(self, mock_query, mock_dgrep):
        # DGrep returns schema-native casing; the TSG lowercases columns.
        df = pd.DataFrame(
            [
                {
                    "PreciseTimeStamp": "2026-04-21T12:48:53Z",
                    "Message": "Upgrade action result: NullReferenceException at ...",
                    "RoleInstance": "BL2PEPF0001A2CB",
                    "STG_TenantName": "MS-BLZ21PrdStr27A",
                    "STG_VirtualTenantName": "MS-BLZ21PrdStrz27A",
                    "STG_PFEnvironment": "BLZ21PrdStr27A-Prod-IAD13P",
                    "Tenant": "XKulfiEastUS-Prod-BL2P",
                },
                {
                    "PreciseTimeStamp": "2026-04-21T12:47:44Z",
                    "Message": "Upgrade action result: State=Failed",
                    "RoleInstance": "BL2PEPF0001A2CB",
                    "STG_TenantName": "MS-BLZ21PrdStr27A",
                    "STG_VirtualTenantName": "MS-BLZ21PrdStrz27A",
                    "STG_PFEnvironment": "BLZ21PrdStr27A-Prod-IAD13P",
                    "Tenant": "XKulfiEastUS-Prod-BL2P",
                },
            ]
        )
        mock_query.return_value = _make_dgrep_result(df)
        mock_dgrep.get_dgrep_link.return_value = ""

        tsg = _make_step2_tsg()
        await tsg.step_2_fetch_failure_logs(_make_input())

        assert len(tsg.failure_logs) == 2
        first = tsg.failure_logs[0]
        # Ordering — newest first (sort by precisetimestamp desc).
        assert first["ts"] == "2026-04-21T12:48:53Z"
        assert first["role_instance"] == "BL2PEPF0001A2CB"
        assert first["stg_tenant"] == "MS-BLZ21PrdStr27A"
        assert first["stg_virtual_tenant"] == "MS-BLZ21PrdStrz27A"
        assert first["stg_pf_environment"] == "BLZ21PrdStr27A-Prod-IAD13P"
        # Exception extraction from message body.
        assert first["exception_type"] == "NullReferenceException"
        # Second row has no exception token.
        assert tsg.failure_logs[1]["exception_type"] == ""

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_rows_are_capped_at_max_failure_rows(self, mock_query, mock_dgrep):
        # Generate 80 rows with descending timestamps; cap is 50.
        rows = [
            {
                "PreciseTimeStamp": f"2026-04-21T12:{i:02d}:00Z",
                "Message": f"row-{i}",
                "RoleInstance": "X",
                "STG_TenantName": "X",
                "STG_VirtualTenantName": "X",
                "STG_PFEnvironment": "X",
                "Tenant": "X",
            }
            for i in range(80)
        ]
        mock_query.return_value = _make_dgrep_result(pd.DataFrame(rows))
        mock_dgrep.get_dgrep_link.return_value = ""

        tsg = _make_step2_tsg()
        await tsg.step_2_fetch_failure_logs(_make_input())

        assert len(tsg.failure_logs) == XKulfiUpgradeActionFailure._MAX_FAILURE_ROWS == 50

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_empty_result_yields_no_rows_and_does_not_raise(
        self, mock_query, mock_dgrep,
    ):
        mock_query.return_value = _make_dgrep_result(pd.DataFrame())
        mock_dgrep.get_dgrep_link.return_value = ""

        tsg = _make_step2_tsg()
        await tsg.step_2_fetch_failure_logs(_make_input())
        assert tsg.failure_logs == []

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_query_skipped_when_dgrep_tenant_missing(
        self, mock_query, mock_dgrep,
    ):
        tsg = _make_step2_tsg(dgrep_tenant=None)
        await tsg.step_2_fetch_failure_logs(_make_input())
        # Neither the link builder nor the query helper should have been
        # called — Step 2 bails out early per step-2-fetch-failure-logs.md.
        assert not mock_dgrep.get_dgrep_link.called
        assert not mock_query.called
        assert tsg.failure_logs == []
        assert tsg.dgrep_link == ""

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_query_skipped_when_alert_keyword_missing(
        self, mock_query, mock_dgrep,
    ):
        tsg = _make_step2_tsg(alert_keyword=None)
        await tsg.step_2_fetch_failure_logs(_make_input())
        assert not mock_query.called
        assert tsg.failure_logs == []

    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep")
    @patch("zerotoil.tsgs.xkulfi_upgrade_action_failure.dgrep_query_with_retry")
    async def test_quote_in_alert_keyword_is_escaped(self, mock_query, mock_dgrep):
        """A `"` in the keyword body would break the MQL string literal —
        Step 2 must escape it to ``\\"``."""
        mock_query.return_value = _make_dgrep_result(pd.DataFrame())
        mock_dgrep.get_dgrep_link.return_value = ""

        tsg = _make_step2_tsg(alert_keyword='Upgrade action "weird" for [x]')
        await tsg.step_2_fetch_failure_logs(_make_input())

        _, kwargs = mock_query.call_args
        assert 'message.contains("Upgrade action \\"weird\\" for [x]")' in kwargs["server_query"]

