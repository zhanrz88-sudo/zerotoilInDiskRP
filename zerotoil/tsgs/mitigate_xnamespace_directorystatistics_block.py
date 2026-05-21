"""Mitigate XNamespaceDirectoryStatistics Block TSG.

Generated from: zero-toil/tsgs/mitigate-xnamespace-directorystatistics-block/
Source: https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/Failover%20blocked%20by%20XnamespaceDirectoryStatistics.md
"""

from typing import Optional

from pydantic import ConfigDict
from xportal import acis, dgrep, icm

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput


class ManualActionRequired(Exception):
    """Raised when a TSG step requires human intervention."""


# ── Input / Output models ───────────────────────────────────


class MitigateXnamespaceDirectorystatisticsBlockInput(TsgInput):
    """Input for Mitigate XNamespaceDirectoryStatistics Block TSG."""

    model_config = ConfigDict(extra='forbid')

    tenant_name: str
    versioned_account_name: str
    environment: str = "Public"


class MitigateXnamespaceDirectorystatisticsBlockOutput(TsgOutput):
    """Output from Mitigate XNamespaceDirectoryStatistics Block TSG."""

    model_config = ConfigDict(extra='forbid')

    ga_invocation_id: str = ""
    mitigation_executed: bool = False
    post_check_stage: str = ""


# ── TSG class ────────────────────────────────────────────────


class MitigateXnamespaceDirectorystatisticsBlock(TsgBase):
    """Apply known mitigation for failover blocked by XNamespaceDirectoryStatistics.

    Steps:
        1. Confirm known signature in primary logs
        2. Execute Geneva action (GeoHelper cleanup)
        3. Verify failover progression and record outcome
    """

    input_type = MitigateXnamespaceDirectorystatisticsBlockInput
    output_type = MitigateXnamespaceDirectorystatisticsBlockOutput

    # intermediate state
    signature_found: bool = False
    ga_invocation_id: str = ""
    mitigation_executed: bool = False
    post_check_stage: str = ""

    async def _run(
        self,
        tsg_input: MitigateXnamespaceDirectorystatisticsBlockInput,
    ) -> MitigateXnamespaceDirectorystatisticsBlockOutput:
        await self.run_step(self._step_1_confirm_signature, tsg_input)

        if not self.signature_found:
            print("  Known signature not found — routing to escalation")
            return MitigateXnamespaceDirectorystatisticsBlockOutput(
                mitigation_executed=False,
            )

        await self.run_step(self._step_2_execute_action, tsg_input)
        await self.run_step(self._step_3_verify_and_record, tsg_input)

        return MitigateXnamespaceDirectorystatisticsBlockOutput(
            ga_invocation_id=self.ga_invocation_id,
            mitigation_executed=self.mitigation_executed,
            post_check_stage=self.post_check_stage,
        )

    # ── Step 1 — Confirm known signature ─────────────────────

    async def _step_1_confirm_signature(
        self,
        tsg_input: MitigateXnamespaceDirectorystatisticsBlockInput,
    ) -> None:
        """Check for XNamespaceDirectoryStatistics error signature in logs.

        Coding ability: dgrep-query
        AUTOMATABLE: Yes
        """
        from datetime import datetime, timedelta

        # TODO: Open Question — Which log source is canonical:
        # XACServer cosmos logs or DGrep mirrored events?
        # Using broad DGrep search for now.
        to_time = datetime.utcnow()
        from_time = to_time - timedelta(hours=4)

        result = await dgrep.query(
            namespaces="RegionalSRP",
            event_names="AccountFailoverStatisticsEvent",
            from_time=from_time,
            to_time=to_time,
            server_query=(
                f'where it.any("XNamespaceDirectoryStatistics") '
                f'select PreciseTimeStamp, accountName, PrimaryStage'
            ),
            server_query_type="MQL",
            scope_conditions={"Tenant": tsg_input.tenant_name},
        )
        df = result.to_df()

        if not df.empty:
            self.signature_found = True
            print("  Known signature found: XNamespaceDirectoryStatistics block")
        else:
            self.signature_found = False
            print("  Known signature NOT found — this may not be the right mitigation")

    # ── Step 2 — Execute Geneva action ───────────────────────

    async def _step_2_execute_action(
        self,
        tsg_input: MitigateXnamespaceDirectorystatisticsBlockInput,
    ) -> None:
        """Execute GeoHelper cleanup action.

        Coding ability: geneva-action-call
        AUTOMATABLE: Partially (requires human approval)
        """
        # TODO: Open Question — What is the exact ACIS extension and
        # operation_id for this GeoHelper action?
        # APPROVAL_GATE: This is a mutating Geneva Action
        print("=" * 60)
        print("APPROVAL REQUIRED: Execute GeoHelper Geneva Action")
        print(f"  Tenant: {tsg_input.tenant_name}")
        print(f"  Account: {tsg_input.versioned_account_name}")
        print("  Action: clean up rows in new tables to unblock failover")
        print("  Table: XNamespaceDirectoryStatistics")
        print("=" * 60)
        raise ManualActionRequired(
            "GeoHelper Geneva Action requires human approval and a validated "
            "operation-id mapping. Execute via Geneva Actions portal: "
            "GeoHelper → 'clean up rows in new tables to unblock failover' "
            f"with Tenant={tsg_input.tenant_name}, "
            f"TableName=XNamespaceDirectoryStatistics, "
            f"AccountName={tsg_input.versioned_account_name}"
        )

    # ── Step 3 — Verify and record ───────────────────────────

    async def _step_3_verify_and_record(
        self,
        tsg_input: MitigateXnamespaceDirectorystatisticsBlockInput,
    ) -> None:
        """Verify failover progression and record outcome in ICM.

        Coding ability: dgrep-query, icm-get-incident
        AUTOMATABLE: Yes
        """
        from datetime import datetime, timedelta

        to_time = datetime.utcnow()
        from_time = to_time - timedelta(hours=1)

        result = await dgrep.query(
            namespaces="RegionalSRP",
            event_names="AccountFailoverStatisticsEvent",
            from_time=from_time,
            to_time=to_time,
            server_query=(
                f'where accountName.Contains("{tsg_input.versioned_account_name}") '
                'select PreciseTimeStamp, accountName, PrimaryStage, SecondaryStage'
            ),
            server_query_type="MQL",
            scope_conditions={"Tenant": tsg_input.tenant_name},
        )
        df = result.to_df()

        if not df.empty:
            last_row = df.sort_values("PreciseTimeStamp", ascending=True).iloc[-1]
            self.post_check_stage = str(last_row.get("PrimaryStage", ""))
            self.mitigation_executed = True
            print(f"  Post-mitigation stage: {self.post_check_stage}")
        else:
            self.post_check_stage = "Unknown"
            print("  Could not verify post-mitigation stage")

        # Record in ICM
        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False
        )
        await incident.add_description(
            f"XNamespaceDirectoryStatistics mitigation applied.\n"
            f"  GA invocation: {self.ga_invocation_id}\n"
            f"  Post-check stage: {self.post_check_stage}\n"
            f"  Mitigation executed: {self.mitigation_executed}"
        )
        print(f"  ICM {tsg_input.incident_id}: outcome recorded")
