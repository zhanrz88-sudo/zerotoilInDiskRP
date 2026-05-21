"""FailoverPendingTransaction - PrimaryStuck.PrepareFailover TSG.

Generated from: zero-toil/tsgs/failover-pending-transaction-primary-stuck-prepare-failover/
Source: https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/%5BFailoverPendingTransaction%5D%20Failover%20for%20accounts%20stuck%20on%20PrimaryStuck.PrepareFailover%20in%20XXX.md
"""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from pydantic import ConfigDict
from xportal import dgrep, icm, kusto
from xstore import get_account, xds

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput, dgrep_query_with_retry


class ManualActionRequired(Exception):
    """Raised when a TSG step requires human intervention."""


# ── Stage ordering ───────────────────────────────────────────

_STAGE_ORDER = [
    "NotStarted",
    "PrepareFailover",
    "PollFailover",
    "FinalizeFailover",
    "SoftFinalizeFailover",
    "HardFinalizeFailover",
    "PollFinalizeFailover",
    "DnsSwitch",
    "ShortTermCleanup",
]

# All stage names that represent the FinalizeFailover phase (for routing).
_FINALIZE_STAGES = {"finalizefailover", "softfinalizefailover", "hardfinalizefailover"}


def _stage_index(stage: str) -> int:
    """Return numeric index for a failover stage, or -1 if unknown."""
    for i, s in enumerate(_STAGE_ORDER):
        if s.lower() == stage.strip().lower():
            return i
    return -1


# ── Input / Output models ───────────────────────────────────


class FailoverPendingTransactionInput(TsgInput):
    """Input for FailoverPendingTransaction TSG."""

    model_config = ConfigDict(extra='forbid')

    tenant_name: str
    incident_start_time_utc: datetime
    environment: str = "Production"  # Production / USSec / USNat
    expected_stuck_location: str = ""  # Primary / Secondary
    expected_stuck_stage: str = ""     # e.g. PrepareFailover


class FailoverPendingTransactionOutput(TsgOutput):
    """Output from FailoverPendingTransaction TSG."""

    model_config = ConfigDict(extra='forbid')

    account_name: str = ""
    operation_id: str = ""
    is_completed: bool = False
    stuck_location: str = ""       # Primary / Secondary / Unknown
    stuck_stage: str = ""
    mitigation_status: str = ""    # Transferred / Escalated / NoActionNeeded


# ── TSG class ────────────────────────────────────────────────


class FailoverPendingTransaction(TsgBase):
    """Triage FailoverPendingTransaction - PrimaryStuck.PrepareFailover.

    Steps:
        1. Extract failover context from alert (DGrep)
        2. Check failover completion (DGrep)
        3. Determine stuck stage and side (DGrep)
        4. Diagnose known issues via XDS logs and transfer/escalate (XDS + ICM)
        5. Update incident and close triage loop (ICM)
    """

    input_type = FailoverPendingTransactionInput
    output_type = FailoverPendingTransactionOutput

    # intermediate state
    operation_id: str = ""
    account_name: str = ""
    storage_tenant: str = ""      # home storage tenant for XDS log searches
    geo_pair_tenant: str = ""     # geo-pair storage tenant (for GRS accounts)
    dgrep_links: list[str] = []
    is_completed: bool = False
    stuck_location: str = ""
    stuck_stage: str = ""
    primary_stage: str = ""       # latest PrimaryStage from statistics event
    secondary_stage: str = ""     # latest SecondaryStage from statistics event
    stage_source: str = ""        # "statistics_event", "matched_stuck", "incident_title"
    matched_stuck: str = ""       # e.g. "SecondaryStuck.PrepareFailover" from Step 1
    mitigation_status: str = ""
    mitigation_detail: str = ""
    xds_evidence_summary: str = ""
    alert_timestamp: datetime | None = None  # DGrep alert time; preferred XDS anchor
    expected_stuck_location: str = ""
    expected_stuck_stage: str = ""
    candidate_failovers: list[dict[str, str]] = []
    account_investigation_summaries: list[dict[str, str]] = []
    # Captured rows from DGrep / XDS queries for inclusion in the HTML
    # evidence summary posted to ICM.  Each entry is
    #   {label, link, total_rows, sample_rows, html}
    evidence_log_samples: list[dict[str, Any]] = []
    # True once any code path has posted an evidence body to ICM in this run.
    # Used by ``_step_5_update_incident`` to skip a duplicate description when
    # the action path already posted one with the same content.
    _evidence_posted_to_icm: bool = False
    # Deferred escalation state: collected during candidate loop and acted on
    # once at the end so we exhaust all sampled accounts before "giving up"
    # to XGeo DRI.
    _defer_escalation: bool = False
    _deferred_escalations: list[dict[str, Any]] = []

    # ── Incident input extraction ────────────────────────────
    #
    # Extraction strategy: REGEX
    #
    # ICM title examples:
    #   "[FailoverPendingTransaction] Failover pending for account stuck on
    #    PrimaryStuck.PrepareFailover in RSRPWestEurope"
    #   "[FailoverPendingTransaction] PrimaryStuck.PrepareFailover in
    #    RSRPEastUS2"
    # Tenant name appears after "in" at the end of the title.
    # incident_start_time_utc comes from the ICM CreateDate field.
    # environment defaults to "Public"; override detection via title
    #   keywords "USSec" / "USNat" if present.
    #
    _TITLE_TENANT_PATTERN = r"\bin\s+(RSRP\S+)"
    _TITLE_ENVIRONMENT_PATTERN = r"\b(USSec|USNat)\b"
    _TITLE_STUCK_PATTERN = r"\b(Primary|Secondary)Stuck\.([A-Za-z]+)\b"
    _MAX_SAMPLED_ACCOUNTS = 3
    _SAMPLE_LOG_COUNT = 20

    @staticmethod
    def _dgrep_environment(tenant_name: str, base_environment: str = "Production") -> str:
        """Return the DGrep environment for account-scoped event queries.

        DGrep events like AccountFailoverEvent and AccountFailoverStatisticsEvent
        are scoped to RSRP tenants.  PreProd RSRP tenants (e.g.
        ``RSRPPublicPreprodEastUS2``) require ``environment="Test"`` to reach
        the correct DGrep endpoint; otherwise uses the TSG input environment.
        """
        if "preprod" in tenant_name.lower():
            return "Test"
        return base_environment

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> FailoverPendingTransactionInput:
        """Extract tenant name, start time, and environment from ICM.

        Uses regex on the incident title (simple, deterministic).
        Falls back to searching description entries if the title does
        not contain the expected pattern.
        """
        title = incident.Title or ""

        # -- tenant_name: from title ---------------------------------
        match = re.search(self._TITLE_TENANT_PATTERN, title, re.IGNORECASE)
        tenant_name = match.group(1) if match else ""

        # Fallback: scan descriptions if the title didn't match
        if not tenant_name:
            descriptions = getattr(incident, "Descriptions", None) or []
            for desc in descriptions:
                text = getattr(desc, "Text", None) or ""
                m = re.search(self._TITLE_TENANT_PATTERN, text, re.IGNORECASE)
                if m:
                    tenant_name = m.group(1)
                    break

        if not tenant_name:
            raise ValueError(
                f"Could not extract tenant_name from incident {incident_id} "
                f"title: {title!r}"
            )

        # -- incident_start_time_utc: from ICM CreateDate ------------
        incident_start_time_utc: datetime = incident.CreateDate

        # -- environment: detect sovereign cloud from title ----------
        env_match = re.search(self._TITLE_ENVIRONMENT_PATTERN, title)
        environment = env_match.group(1) if env_match else "Production"

        # -- expected stuck location/stage from title ----------------
        stuck_match = re.search(self._TITLE_STUCK_PATTERN, title, re.IGNORECASE)
        expected_stuck_location = ""
        expected_stuck_stage = ""
        if stuck_match:
            expected_stuck_location = stuck_match.group(1).title()
            expected_stuck_stage = stuck_match.group(2)

        print(f"  Extracted from incident {incident_id}:")
        print(f"    tenant_name            = {tenant_name}")
        print(f"    incident_start_time_utc = {incident_start_time_utc}")
        print(f"    environment            = {environment}")
        print(f"    expected_stuck_location = {expected_stuck_location or 'Unknown'}")
        print(f"    expected_stuck_stage    = {expected_stuck_stage or 'Unknown'}")

        return FailoverPendingTransactionInput(
            incident_id=incident_id,
            tenant_name=tenant_name,
            incident_start_time_utc=incident_start_time_utc,
            environment=environment,
            expected_stuck_location=expected_stuck_location,
            expected_stuck_stage=expected_stuck_stage,
        )

    async def _run(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> FailoverPendingTransactionOutput:
        self.dgrep_links = []
        self.candidate_failovers = []
        self.expected_stuck_location = tsg_input.expected_stuck_location
        self.expected_stuck_stage = tsg_input.expected_stuck_stage
        self.account_investigation_summaries = []
        self.evidence_log_samples = []
        self._evidence_posted_to_icm = False
        self._deferred_escalations = []
        self._defer_escalation = True

        await self.run_step(self._step_1_extract_failover_context, tsg_input)

        if not self.candidate_failovers:
            print("No candidate failover contexts found in Step 1.")
        else:
            print(
                f"Investigating {len(self.candidate_failovers)} sampled account(s) "
                f"from alert context..."
            )

        successful_action = False
        for idx, candidate in enumerate(self.candidate_failovers, start=1):
            self._set_active_candidate(candidate)

            print(
                f"\n=== Candidate {idx}/{len(self.candidate_failovers)}: "
                f"account={self.account_name}, operation={self.operation_id}, "
                f"matched_stuck={candidate.get('matched_stuck', '') or 'Unknown'} ==="
            )

            try:
                await self.run_step(self._step_2_check_failover_completion, tsg_input)

                if self.is_completed:
                    self.mitigation_status = "NoActionNeeded"
                    print("Failover already completed -- no action needed.")
                    successful_action = True
                else:
                    await self.run_step(self._step_3_determine_stuck_stage, tsg_input)
                    await self._resolve_storage_tenants(tsg_input)

                    no_stage_signal = (
                        self.stuck_location == "Unknown"
                        and (not self.stuck_stage or self.stuck_stage == "Unknown")
                    )
                    is_last_candidate = idx == len(self.candidate_failovers)
                    if no_stage_signal and not is_last_candidate:
                        self.mitigation_status = ""
                        self.mitigation_detail = (
                            "No stage signal for this sampled account; "
                            "continuing with next sampled account."
                        )
                        print("  No stage signal for this account; trying next sampled account")
                    else:
                        await self.run_step(self._step_4_mitigate_or_escalate, tsg_input)

                        # A successful Transfer is a real action; stop here.
                        # "EscalationDeferred" means we found no known issue for THIS
                        # account but want to try remaining sampled accounts before
                        # finally escalating to XGeo DRI.
                        if self.mitigation_status == "Transferred":
                            successful_action = True
                            print("  Action taken for this candidate; stopping further candidate processing")
                            break
                        if self.mitigation_status == "EscalationDeferred" and not is_last_candidate:
                            print("  No known issue for this account; trying next sampled account")
            except ManualActionRequired as e:
                print(f"  Candidate requires manual action: {e}")
                if not self.mitigation_status:
                    self.mitigation_status = "ManualActionRequired"
                if not self.mitigation_detail:
                    self.mitigation_detail = str(e)
                break
            except Exception as e:
                print(f"  Candidate investigation failed and will continue: {type(e).__name__}: {e}")
            finally:
                self._record_active_candidate_result(candidate)

        # Exit defer mode and, if no candidate produced an action, perform a
        # single combined escalation that aggregates evidence from every
        # sampled account.
        self._defer_escalation = False
        if not successful_action and self._deferred_escalations:
            try:
                await self._perform_deferred_escalation(tsg_input)
            except ManualActionRequired as e:
                print(f"  Final escalation requires manual action: {e}")
                if not self.mitigation_detail:
                    self.mitigation_detail = str(e)

        self._apply_primary_summary_result()

        await self.run_step(self._step_5_update_incident, tsg_input)

        return FailoverPendingTransactionOutput(
            account_name=self.account_name,
            operation_id=self.operation_id,
            is_completed=self.is_completed,
            stuck_location=self.stuck_location,
            stuck_stage=self.stuck_stage,
            mitigation_status=self.mitigation_status,
        )

    def _set_active_candidate(self, candidate: dict[str, str]) -> None:
        """Set state for investigating one sampled account/operation."""
        self.operation_id = candidate.get("operation_id", "")
        self.account_name = candidate.get("account_name", "")
        self.matched_stuck = candidate.get("matched_stuck", "")
        self.storage_tenant = ""
        self.geo_pair_tenant = ""
        self.is_completed = False
        self.stuck_location = ""
        self.stuck_stage = ""
        self.primary_stage = ""
        self.secondary_stage = ""
        self.stage_source = ""  # "statistics_event", "matched_stuck", "incident_title"
        self.mitigation_status = ""
        self.mitigation_detail = ""
        self.xds_evidence_summary = ""

        # Parse the DGrep alert timestamp for use as XDS search anchor.
        raw_ts = candidate.get("alert_timestamp", "")
        self.alert_timestamp = None
        if raw_ts:
            try:
                dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                self.alert_timestamp = dt
                print(f"  XDS anchor: DGrep alert timestamp {self.alert_timestamp.isoformat()}")
            except (ValueError, TypeError):
                print(f"  WARNING: Could not parse alert_timestamp '{raw_ts}'; falling back to incident time")

    def _print_df_sample(self, df: Any) -> None:
        """Print a bounded sample of dataframe rows using central verbosity control."""
        if df is None or df.empty:
            return
        print(f"  Sample (first {self._SAMPLE_LOG_COUNT}):")
        print(df.head(self._SAMPLE_LOG_COUNT).to_string(index=False))

    def _record_log_sample(
        self,
        label: str,
        link: str,
        df: Any,
        max_rows: int = 5,
        message_max: int = 400,
    ) -> None:
        """Capture a small HTML-renderable sample of a query result for ICM.

        Stored on ``self.evidence_log_samples`` and rendered later by
        ``_build_evidence_summary_html``.  Long ``message`` columns are
        truncated to ``message_max`` characters per row to keep the ICM
        description readable.  The full result is still available through
        the DGrep / XDS search link.
        """
        if df is None or len(df) == 0:
            self.evidence_log_samples.append(
                {
                    "label": label,
                    "link": link or "",
                    "total_rows": 0,
                    "sample_rows": 0,
                    "html": "",
                }
            )
            return

        sample = df.head(max_rows).copy()
        for col in sample.columns:
            if col.lower() == "message":
                sample[col] = sample[col].astype(str).str.slice(0, message_max)
        try:
            html = sample.to_html(index=False, border=0, escape=True)
        except Exception:
            html = f"<pre>{sample.to_string(index=False)}</pre>"

        self.evidence_log_samples.append(
            {
                "label": label,
                "link": link or "",
                "total_rows": int(len(df)),
                "sample_rows": int(len(sample)),
                "html": html,
            }
        )

    def _record_active_candidate_result(self, candidate: dict[str, str]) -> None:
        """Persist per-account investigation results for final incident evidence."""
        self.account_investigation_summaries.append(
            {
                "account_name": self.account_name,
                "operation_id": self.operation_id,
                "matched_stuck": candidate.get("matched_stuck", ""),
                "is_completed": str(self.is_completed),
                "stuck_location": self.stuck_location,
                "stuck_stage": self.stuck_stage,
                "primary_stage": self.primary_stage,
                "secondary_stage": self.secondary_stage,
                "stage_source": self.stage_source,
                "mitigation_status": self.mitigation_status,
                "mitigation_detail": self.mitigation_detail,
                "xds_evidence_summary": self.xds_evidence_summary,
            }
        )

    def _apply_primary_summary_result(self) -> None:
        """Choose a representative candidate result for the typed TSG output."""
        if not self.account_investigation_summaries:
            return

        # Prefer entries with actionable status over empty/inconclusive ones.
        for status in ["Transferred", "Escalated", "EscalationDeferred", "NoActionNeeded", ""]:
            for summary in self.account_investigation_summaries:
                if summary.get("mitigation_status", "") == status:
                    self.account_name = summary.get("account_name", "")
                    self.operation_id = summary.get("operation_id", "")
                    self.is_completed = summary.get("is_completed", "False") == "True"
                    self.stuck_location = summary.get("stuck_location", "")
                    self.stuck_stage = summary.get("stuck_stage", "")
                    self.primary_stage = summary.get("primary_stage", "")
                    self.secondary_stage = summary.get("secondary_stage", "")
                    self.stage_source = summary.get("stage_source", "")
                    self.mitigation_status = summary.get("mitigation_status", "")
                    self.mitigation_detail = summary.get("mitigation_detail", "")
                    self.xds_evidence_summary = summary.get("xds_evidence_summary", "")
                    return

    # ── Helper: Resolve storage tenants for XDS log search ───

    async def _resolve_storage_tenants(self, tsg_input: FailoverPendingTransactionInput) -> None:
        """Resolve the home storage tenant and geo-pair from the account name.

        XDS logs live on the **storage tenant** (e.g. ``MS-MEL23PrdStr11D``),
        which is the physical stamp that hosts the customer's data.  The
        **SRP tenant** (e.g. ``RSRPAustraliaEast``, ``RSRPPublicPreprodEastUS2``)
        is a *control-plane* stamp that allocates / fails over accounts but
        does NOT host XDS role-instance logs.  See coding ability
        ``storage-account-tenant-metadata`` for the full distinction --
        substituting the SRP tenant for the storage tenant is always wrong.

        Backend / PreProd caveat
        ------------------------
        ``xstore.get_account`` shipped on the XJupyterLite backend image
        (older version) only consults the XDS account metadata service.
        The local ``zero-toil/.venv`` ships a newer version that falls
        back to Kusto via the XPortal AccountMetadata REST API, which
        covers accounts that the XDS service does not return -- including
        many RSRP PreProd test accounts.  When the backend version raises
        ``StorageAccountNotFoundError`` for a PreProd account that DOES
        exist, the proper fix is to upgrade the backend ``xstore`` image
        (tracked as the ``preprod-env-mapping`` follow-up).  In the
        meantime we cannot resolve the storage tenant, so Step 4 falls
        back to its existing 'no storage tenant' branch (Branch E /
        default escalation) instead of inventing a fake tenant.
        """
        if not self.account_name:
            print("  Cannot resolve storage tenant -- no account name")
            return

        try:
            account_entity = await get_account(self.account_name, environment=tsg_input.environment)
            self.storage_tenant = account_entity.TenantName or ""
            self.geo_pair_tenant = account_entity.GeoPairName or ""
            print(f"  Account type: {account_entity.AccountType}")
            print(f"  Storage tenant (home): {self.storage_tenant}")
            print(f"  Geo-pair tenant: {self.geo_pair_tenant}")
        except Exception as e:
            print(f"  WARNING: Could not resolve storage tenant for '{self.account_name}': {e}")
            print(
                "  NOTE: storage_tenant left empty. XDS log search in Step 4 "
                "will skip via the 'no storage tenant' branch. Do NOT substitute "
                "the SRP/RSRP tenant -- XDS logs do not live on SRP tenants."
            )

    # ── Step 1 — Extract failover context from alert ─────────

    async def _step_1_extract_failover_context(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Query DGrep for the pending failover operation context.

        Coding ability: dgrep-query
        AUTOMATABLE: Yes
        """
        from_time = tsg_input.incident_start_time_utc - timedelta(hours=3)
        to_time = tsg_input.incident_start_time_utc + timedelta(minutes=30)

        # Query 1: Find pending failover alert events in small chunks to reduce
        # throttling risk. Failed chunks are skipped and the rest are merged.
        chunk_size = timedelta(minutes=30)
        chunk_start = from_time
        merged_df = None

        while chunk_start < to_time:
            chunk_end = min(chunk_start + chunk_size, to_time)
            print(
                "  DGrep chunk (ServiceBackgroundActivityEvent): "
                f"{chunk_start.isoformat()} -> {chunk_end.isoformat()}"
            )

            chunk_result = None
            try:
                chunk_result = await dgrep_query_with_retry(
                    dgrep,
                    namespaces="RegionalSRP",
                    event_names="ServiceBackgroundActivityEvent",
                    from_time=chunk_start,
                    to_time=chunk_end,
                    server_query=(
                        'where it.any("LogPendingFailoverTransactionAlertEvent") '
                        'select PreciseTimeStamp, Message, ActivityId'
                    ),
                    server_query_type="MQL",
                    scope_conditions={"Tenant": tsg_input.tenant_name},
                    environment=tsg_input.environment,
                )
            except Exception as exc:
                print(
                    "  WARNING: DGrep chunk failed after retries; "
                    f"skipping chunk {chunk_start.isoformat()} -> {chunk_end.isoformat()}: {exc}"
                )

            if chunk_result is not None:
                chunk_df = chunk_result.to_df()
                dgrep_link = chunk_result.get_dgrep_link()
                self.dgrep_links.append(dgrep_link)
                print(f"  DGrep link: {dgrep_link}")
                print(f"  Chunk results: {len(chunk_df)} rows")

                if merged_df is None:
                    merged_df = chunk_df
                else:
                    merged_df = merged_df._append(chunk_df, ignore_index=True)

            chunk_start = chunk_end
            # Throttle between chunks to avoid saturating DGrep query quota
            if chunk_start < to_time:
                await asyncio.sleep(3)

        df = merged_df
        if df is None:
            print("  Results: 0 rows")
        else:
            print(f"  Results: {len(df)} rows")

        if df is not None and not df.empty:
            self._print_df_sample(df)
            self._record_log_sample(
                "DGrep ServiceBackgroundActivityEvent (PendingFailover alerts)",
                self.dgrep_links[0] if self.dgrep_links else "",
                df,
            )
        else:
            print("WARNING: No pending failover alert events found in DGrep")
            print("  Check DGrep manually or widen time window")
            return

        # DGrep returns schema-native column names which may differ in case
        # from the MQL select aliases.  Normalize to lowercase for reliable access.
        df.columns = df.columns.str.lower()

        # Parse candidate operation/account pairs and correlate with the metric
        # row that carries the stuck label (for example SecondaryStuck.SoftFinalizeFailover).
        op_id_pattern = r"OperationId:\s*([0-9a-fA-F\-]{36})"
        acct_pattern = r"account name:\s*(\S+?)(?:FailoverType|,|\])"
        stuck_pattern = r"dimensionValues:\s*((?:Primary|Secondary)Stuck\.[A-Za-z]+)"
        # Parse the operation StartTimeInUtc so we can prefer more-recently
        # started failover operations when picking which candidates to sample.
        # Example fragment in the message:
        #   "StartTimeInUtc: 5/5/2026 8:50:21 AM]"
        start_time_pattern = r"StartTimeInUtc:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}\s+[0-9]{1,2}:[0-9]{2}:[0-9]{2}\s*(?:AM|PM)?)"

        # First pass: collect operation/account rows and metric rows by activity id.
        per_activity: dict[str, dict[str, str]] = {}
        for _, row in df.iterrows():
            msg = str(row.get("message", ""))
            activity_id = str(row.get("activityid", "") or "")
            if not activity_id:
                continue

            entry = per_activity.setdefault(
                activity_id,
                {
                    "activity_id": activity_id,
                    "operation_id": "",
                    "account_name": "",
                    "matched_stuck": "",
                    "sample_timestamp": str(row.get("precisetimestamp", "")),
                    "start_time_in_utc_raw": "",
                },
            )

            op_match = re.search(op_id_pattern, msg)
            if op_match and not entry["operation_id"]:
                entry["operation_id"] = op_match.group(1)
                acct_match = re.search(acct_pattern, msg)
                if acct_match:
                    entry["account_name"] = acct_match.group(1)

            start_match = re.search(start_time_pattern, msg)
            if start_match and not entry["start_time_in_utc_raw"]:
                entry["start_time_in_utc_raw"] = start_match.group(1).strip()

            stuck_match = re.search(stuck_pattern, msg, re.IGNORECASE)
            if stuck_match:
                entry["matched_stuck"] = stuck_match.group(1)

        candidates = [
            c for c in per_activity.values()
            if c.get("operation_id") and c.get("account_name")
        ]

        # Fallback: if we found operations but no account names, try resolving
        # via AccountFailoverStatisticsEvent (second DGrep query).
        ops_without_account = [
            c for c in per_activity.values()
            if c.get("operation_id") and not c.get("account_name")
        ]
        if not candidates and ops_without_account:
            fallback_op = ops_without_account[0]["operation_id"]
            print(f"  No account names parsed; falling back to AccountFailoverStatisticsEvent for op {fallback_op}")
            result2 = await dgrep_query_with_retry(
                dgrep,
                namespaces="RegionalSRP",
                event_names="AccountFailoverStatisticsEvent",
                from_time=from_time,
                to_time=to_time,
                server_query=(
                    f'where it.any("{fallback_op}") '
                    'select PreciseTimeStamp, accountName, operationId'
                ),
                server_query_type="MQL",
                scope_conditions={"Tenant": tsg_input.tenant_name},
                environment=tsg_input.environment,
            )
            df2 = result2.to_df()
            dgrep_link2 = result2.get_dgrep_link()
            self.dgrep_links.append(dgrep_link2)
            print(f"  DGrep link (AccountFailoverStatisticsEvent): {dgrep_link2}")
            print(f"  Results: {len(df2)} rows")
            if not df2.empty:
                self._print_df_sample(df2)
                df2.columns = df2.columns.str.lower()
                resolved_account = str(df2.iloc[0].get("accountname", ""))
                if resolved_account:
                    # Patch all ops_without_account entries with the resolved name
                    for c in ops_without_account:
                        c["account_name"] = resolved_account
                    candidates = [
                        c for c in per_activity.values()
                        if c.get("operation_id") and c.get("account_name")
                    ]
            else:
                print("  WARNING: No AccountFailoverStatisticsEvent records found")

        expected_stuck = ""
        if tsg_input.expected_stuck_location and tsg_input.expected_stuck_stage:
            expected_stuck = f"{tsg_input.expected_stuck_location}Stuck.{tsg_input.expected_stuck_stage}".lower()

        if expected_stuck:
            filtered = [
                c for c in candidates
                if c.get("matched_stuck", "").lower() == expected_stuck
            ]
            print(
                f"  Candidates before stuck-pattern filter: {len(candidates)}; "
                f"after filter ({expected_stuck}): {len(filtered)}"
            )
            if filtered:
                candidates = filtered
            else:
                print("  WARNING: No candidates matched title stuck pattern; using unfiltered candidates")

        # Deduplicate by operation/account, keeping the entry with the latest
        # alert timestamp (so the XDS anchor is as recent as possible).  When
        # the same op/account appears multiple times, also retain the latest
        # parsed StartTimeInUtc.
        deduped: list[dict[str, str]] = []
        seen_keys: dict[str, int] = {}
        for candidate in candidates:
            key = f"{candidate.get('operation_id', '')}|{candidate.get('account_name', '')}"
            ts = candidate.get("sample_timestamp", "")
            start_raw = candidate.get("start_time_in_utc_raw", "")
            if key in seen_keys:
                existing_idx = seen_keys[key]
                existing_ts = deduped[existing_idx].get("alert_timestamp", "")
                if ts > existing_ts:
                    deduped[existing_idx]["alert_timestamp"] = ts
                if start_raw and not deduped[existing_idx].get("start_time_in_utc_raw"):
                    deduped[existing_idx]["start_time_in_utc_raw"] = start_raw
                continue
            candidate["alert_timestamp"] = ts
            seen_keys[key] = len(deduped)
            deduped.append(candidate)

        # Sort candidates so the most recent log message wins (primary key)
        # and, on ties, the more recently started failover operation wins
        # (secondary key).  This makes the sampled set bias toward the
        # freshest evidence — important when the SLA-breach alert fires
        # repeatedly and we can only investigate _MAX_SAMPLED_ACCOUNTS.
        def _parse_start_time(raw: str) -> datetime:
            if not raw:
                return datetime.min.replace(tzinfo=timezone.utc)
            for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
                try:
                    return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            return datetime.min.replace(tzinfo=timezone.utc)

        deduped.sort(
            key=lambda c: (
                c.get("alert_timestamp", "") or "",
                _parse_start_time(c.get("start_time_in_utc_raw", "")),
            ),
            reverse=True,
        )

        self.candidate_failovers = deduped[: self._MAX_SAMPLED_ACCOUNTS]
        print(f"  Sampled candidate accounts: {len(self.candidate_failovers)}")
        for i, candidate in enumerate(self.candidate_failovers, start=1):
            print(
                f"    {i}. account={candidate.get('account_name', '')}, "
                f"operation={candidate.get('operation_id', '')}, "
                f"stuck={candidate.get('matched_stuck', '') or 'Unknown'}, "
                f"alert_ts={candidate.get('alert_timestamp', '') or 'Unknown'}, "
                f"start_time={candidate.get('start_time_in_utc_raw', '') or 'Unknown'}"
            )

        if not self.candidate_failovers:
            print("WARNING: Could not parse any candidate operation/account from alert messages")
            return

        # Keep first candidate in legacy fields so downstream logic remains valid.
        self.operation_id = self.candidate_failovers[0].get("operation_id", "")
        self.account_name = self.candidate_failovers[0].get("account_name", "")

        print(f"  primary operation_id = {self.operation_id}")
        print(f"  primary account_name = {self.account_name}")
        print(f"  DGrep evidence: {self.dgrep_links[0]}")

    # ── Step 2 — Check failover completion ───────────────────

    async def _step_2_check_failover_completion(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Check if the failover already completed.

        Coding ability: dgrep-query
        AUTOMATABLE: Yes
        """
        if not self.account_name:
            print("  Skipping completion check -- no account name resolved")
            return

        from_time = tsg_input.incident_start_time_utc - timedelta(hours=3)
        to_time = datetime.now(timezone.utc)

        dgrep_env = self._dgrep_environment(tsg_input.tenant_name, tsg_input.environment)
        print(f"  DGrep environment: {dgrep_env} (tenant={tsg_input.tenant_name})")

        result = await dgrep_query_with_retry(
            dgrep,
            namespaces="RegionalSRP",
            event_names="AccountFailoverEvent",
            from_time=from_time,
            to_time=to_time,
            server_query=(
                f'where accountName.Contains("{self.account_name}") '
                'select PreciseTimeStamp, accountName, '
                'accountFailoverStatusType, operationId'
            ),
            server_query_type="MQL",
            scope_conditions={"Tenant": tsg_input.tenant_name},
            environment=dgrep_env,
        )
        df = result.to_df()
        dgrep_link = result.get_dgrep_link()
        self.dgrep_links.append(dgrep_link)

        print(f"  DGrep link: {dgrep_link}")
        print(f"  Results: {len(df)} rows")
        if not df.empty:
            self._print_df_sample(df)
            self._record_log_sample(
                f"DGrep AccountFailoverEvent ({self.account_name})",
                dgrep_link, df,
            )
        else:
            print("  No AccountFailoverEvent records found -- failover not complete")
            return

        # Normalize column names (DGrep returns schema-native casing)
        df.columns = df.columns.str.lower()

        # Sort ascending and check for Complete status
        # TODO: Open Question — Can accountFailoverStatusType transiently
        # emit Complete for a prior operation id in the same window?
        df_sorted = df.sort_values("precisetimestamp", ascending=True)
        for _, row in df_sorted.iterrows():
            status = str(row.get("accountfailoverstatustype", ""))
            if status == "Complete":
                self.is_completed = True
                print(f"  Failover COMPLETED at {row.get('precisetimestamp')}")
                return

        latest_status = str(df_sorted.iloc[-1].get("accountfailoverstatustype", ""))
        print(f"  Failover not complete -- latest status: {latest_status}")

    # ── Step 3 — Determine stuck stage and side ──────────────

    async def _step_3_determine_stuck_stage(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Classify where the transaction is blocked.

        Coding ability: dgrep-query
        AUTOMATABLE: Yes

        Fallback chain when AccountFailoverStatisticsEvent returns no data
        (common for RSRP tenants):
        1. candidate matched_stuck from Step 1 alert (e.g. "SecondaryStuck.PrepareFailover")
        2. incident title expected_stuck_location / expected_stuck_stage
        """
        if not self.account_name:
            self.stuck_location = "Unknown"
            self.stuck_stage = "Unknown"
            return

        from_time = tsg_input.incident_start_time_utc - timedelta(hours=3)
        to_time = datetime.now(timezone.utc)

        dgrep_env = self._dgrep_environment(tsg_input.tenant_name, tsg_input.environment)
        print(f"  DGrep environment: {dgrep_env} (tenant={tsg_input.tenant_name})")

        result = await dgrep_query_with_retry(
            dgrep,
            namespaces="RegionalSRP",
            event_names="AccountFailoverStatisticsEvent",
            from_time=from_time,
            to_time=to_time,
            server_query=(
                f'where accountName.Contains("{self.account_name}") '
                'select PreciseTimeStamp, accountName, PrimaryStage, SecondaryStage'
            ),
            server_query_type="MQL",
            scope_conditions={"Tenant": tsg_input.tenant_name},
            environment=dgrep_env,
        )
        df = result.to_df()
        dgrep_link = result.get_dgrep_link()
        self.dgrep_links.append(dgrep_link)

        print(f"  DGrep link: {dgrep_link}")
        print(f"  Results: {len(df)} rows")
        if not df.empty:
            self._print_df_sample(df)
            self._record_log_sample(
                f"DGrep AccountFailoverStatisticsEvent ({self.account_name})",
                dgrep_link, df,
            )
            # Normalize column names (DGrep returns schema-native casing)
            df.columns = df.columns.str.lower()

            # Use the last record as current snapshot
            last_row = df.sort_values("precisetimestamp", ascending=True).iloc[-1]
            primary_stage = str(last_row.get("primarystage", ""))
            secondary_stage = str(last_row.get("secondarystage", ""))

            self.primary_stage = primary_stage
            self.secondary_stage = secondary_stage
            self.stage_source = "statistics_event"

            primary_idx = _stage_index(primary_stage)
            secondary_idx = _stage_index(secondary_stage)

            if primary_idx < 0 and secondary_idx < 0:
                self.stuck_location = "Unknown"
                self.stuck_stage = f"Primary={primary_stage}, Secondary={secondary_stage}"
            elif primary_idx < secondary_idx:
                self.stuck_location = "Primary"
                self.stuck_stage = primary_stage
            elif secondary_idx < primary_idx:
                self.stuck_location = "Secondary"
                self.stuck_stage = secondary_stage
            else:
                self.stuck_location = "Unknown"
                self.stuck_stage = primary_stage

            print(f"  Stuck location: {self.stuck_location}")
            print(f"  Stuck stage: {self.stuck_stage}")
            print(f"  Primary={primary_stage}, Secondary={secondary_stage}")
            return

        # ── Fallback 1: derive from matched_stuck (Step 1 alert data) ──
        print("  No AccountFailoverStatisticsEvent records")
        if self.matched_stuck:
            m = re.match(r"(Primary|Secondary)Stuck\.(\w+)", self.matched_stuck)
            if m:
                side, stage = m.group(1).title(), m.group(2)
                self.stuck_location = side
                self.stuck_stage = stage
                if side == "Primary":
                    self.primary_stage = stage
                else:
                    self.secondary_stage = stage
                self.stage_source = "matched_stuck"
                print(
                    f"  Fallback from matched_stuck: {side} stuck at {stage} "
                    "(only one side known)"
                )
                return

        # ── Fallback 2: derive from incident title ─────────────────────
        if tsg_input.expected_stuck_location and tsg_input.expected_stuck_stage:
            self.stuck_location = tsg_input.expected_stuck_location
            self.stuck_stage = tsg_input.expected_stuck_stage
            if tsg_input.expected_stuck_location == "Primary":
                self.primary_stage = tsg_input.expected_stuck_stage
            else:
                self.secondary_stage = tsg_input.expected_stuck_stage
            self.stage_source = "incident_title"
            print(
                f"  Fallback from incident title: {self.stuck_location} stuck at "
                f"{self.stuck_stage} (only one side known)"
            )
            return

        self.stuck_location = "Unknown"
        self.stuck_stage = "Unknown"
        print("  Cannot determine stage from any source")

    # ── Step 4 — Diagnose known issues and mitigate or escalate ─

    async def _step_4_mitigate_or_escalate(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Diagnose root cause via XDS logs and transfer/escalate.

        Routes on (primary_stage, secondary_stage) pairs per source TSG known-issue matrix.

        Coding ability: xds-log-search, icm-get-incident
        AUTOMATABLE: Partially (XDS search + pattern matching automatable;
                     ICM transfer requires operator confirmation;
                     FinalizeFailover XFiles partition check requires manual action)
        """
        p = self.primary_stage.strip().lower()
        s = self.secondary_stage.strip().lower()
        partial_info = self.stage_source in ("matched_stuck", "incident_title")

        print(
            f"  Routing Step 4 on (primary={self.primary_stage}, "
            f"secondary={self.secondary_stage}, source={self.stage_source})"
        )

        # ── Full two-sided routing (from AccountFailoverStatisticsEvent) ──

        # Branch A: PrepareFailover with one side NotStarted
        if (p == "preparefailover" and s == "notstarted") or \
           (p == "notstarted" and s == "preparefailover"):
            await self._branch_a_prepare_failover(tsg_input)
        # Both sides NotStarted: no known mitigation rule applies, but Branch A's
        # XACServer/TableMaster log searches still produce useful evidence to
        # attach to the escalation.  Branch A will fall through to default
        # escalation if no known split-failure pattern matches.
        elif p == "notstarted" and s == "notstarted":
            print(
                "  Both sides NotStarted -- no known mitigation rule; running "
                "Branch A search to capture evidence before escalating"
            )
            await self._branch_a_prepare_failover(tsg_input)
        # Branch B: Both sides at PrepareFailover → GeoConfigOff check on Primary
        elif p == "preparefailover" and s == "preparefailover":
            await self._branch_b_both_prepare_failover(tsg_input)
        # Branch C: Both sides at FinalizeFailover (incl. Soft/Hard variants)
        elif p in _FINALIZE_STAGES and s in _FINALIZE_STAGES:
            await self._branch_c_finalize_failover(tsg_input)
        # Branch D: Both sides at DnsSwitch → XACServer 0x830a382d check
        elif p == "dnsswitch" and s == "dnsswitch":
            await self._branch_d_dns_switch(tsg_input)

        # ── Single-side fallback (from matched_stuck / incident_title) ──
        # Only one side is known; route based on the known stage.
        elif partial_info and (p and not s) or (s and not p):
            known_stage = (p or s)
            print(f"  Single-side routing (source={self.stage_source}): stage={known_stage}")
            if known_stage == "preparefailover":
                await self._branch_a_prepare_failover(tsg_input)
            elif known_stage in _FINALIZE_STAGES:
                await self._branch_c_finalize_failover(tsg_input)
            elif known_stage == "dnsswitch":
                await self._branch_d_dns_switch(tsg_input)
            else:
                await self._branch_e_default_escalation(tsg_input)

        # Branch E: Default escalation
        else:
            await self._branch_e_default_escalation(tsg_input)

    # ── Branch A — PrepareFailover stuck (Primary or Secondary) ──

    async def _branch_a_prepare_failover(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Diagnose PrepareFailover block via XACServer + TableMaster logs.

        Key principle from source TSG: go to the tenant with the NotStarted side.
        - If secondary is NotStarted → search on geo_pair_tenant (secondary stamp)
        - If primary is NotStarted → search on storage_tenant (primary stamp)
        - If only one side known (single-side fallback) → search both tenants
        """
        p = self.primary_stage.strip().lower()
        s = self.secondary_stage.strip().lower()
        partial_info = self.stage_source in ("matched_stuck", "incident_title")

        if p == "notstarted" and s == "notstarted":
            # Both sides NotStarted: search BOTH tenants since either side may
            # hold the actionable evidence.
            tenants = []
            if self.storage_tenant:
                tenants.append((self.storage_tenant, "primary (home)"))
            if self.geo_pair_tenant and self.geo_pair_tenant != self.storage_tenant:
                tenants.append((self.geo_pair_tenant, "secondary (geo-pair)"))
            search_tenants = tenants if tenants else [(self.storage_tenant, "primary (fallback)")]
            print(f"  Both-NotStarted PrepareFailover: searching {len(search_tenants)} tenant(s)")
        elif s == "notstarted":
            search_tenants = [(self.geo_pair_tenant or self.storage_tenant, "secondary (NotStarted side)")]
        elif p == "notstarted":
            search_tenants = [(self.storage_tenant, "primary (NotStarted side)")]
        elif partial_info:
            # Single-side fallback: search both tenants since we don't know which
            # side is NotStarted.
            tenants = []
            if self.storage_tenant:
                tenants.append((self.storage_tenant, "primary (home)"))
            if self.geo_pair_tenant and self.geo_pair_tenant != self.storage_tenant:
                tenants.append((self.geo_pair_tenant, "secondary (geo-pair)"))
            search_tenants = tenants if tenants else [(self.storage_tenant, "primary (fallback)")]
            print(f"  Single-side PrepareFailover: searching {len(search_tenants)} tenant(s)")
        else:
            search_tenants = [(self.storage_tenant, "primary (fallback)")]

        if not any(t for t, _ in search_tenants if t):
            print("  No storage tenant resolved -- cannot search XDS logs")
            await self._branch_e_default_escalation(tsg_input)
            return

        # XDS log search time windows (CRITICAL constraints):
        #   Verbose: max 5 minutes (extremely high volume)
        #   Error:   max 30 minutes
        # Prefer the DGrep alert timestamp as anchor — it tracks actual
        # failover activity which can precede ICM creation by hours.
        event_time = self.alert_timestamp or tsg_input.incident_start_time_utc
        anchor_source = "alert_timestamp" if self.alert_timestamp else "incident_start_time_utc"
        print(f"  XDS time anchor: {event_time.isoformat()} (source={anchor_source})")
        verbose_from = event_time - timedelta(minutes=2)
        verbose_to = event_time + timedelta(minutes=2)
        error_from = event_time - timedelta(minutes=15)
        error_to = event_time + timedelta(minutes=15)

        all_xac_links: list[str] = []
        all_tm_links: list[str] = []
        combined_xac_df = None
        combined_tm_df = None

        for search_tenant, side_label in search_tenants:
            if not search_tenant:
                continue

            print(f"  Branch A: searching {side_label} tenant={search_tenant}")

            # A1. XACServer verbose
            print(f"  Searching XACServer verbose on {search_tenant} for '{self.account_name}'...")
            print(f"    Window: {verbose_from} -> {verbose_to}, top=50")
            xac_result = await xds.search_log(
                search_tenant,
                verbose_from,
                verbose_to,
                ['xacserver'],
                log_type='Verbose',
                search_string=self.account_name,
                top=50,
            )
            xac_df = xac_result.to_df()
            print(f"  XACServer verbose results: {len(xac_df)} rows")
            if not xac_df.empty:
                self._print_df_sample(xac_df)
                combined_xac_df = xac_df if combined_xac_df is None else pd.concat([combined_xac_df, xac_df])

            xac_link = await xds.generate_log_search_link(
                search_tenant,
                verbose_from,
                verbose_to,
                ['xacserver'],
                log_type='Verbose',
                search_string=self.account_name,
            )
            all_xac_links.append(xac_link)
            self._record_log_sample(
                f"XACServer Verbose ({side_label}, {search_tenant})",
                xac_link, xac_df,
            )
            print(f"  XACServer log search link: {xac_link}")

            # A2. TableMaster error
            print(f"  Searching TableMaster error on {search_tenant} for '{self.account_name}'...")
            print(f"    Window: {error_from} -> {error_to}, top=100")
            tm_result = await xds.search_log(
                search_tenant,
                error_from,
                error_to,
                ['xtablemaster'],
                log_type='Error',
                search_string=self.account_name,
                top=100,
            )
            tm_df = tm_result.to_df()
            print(f"  TableMaster error results: {len(tm_df)} rows")
            if not tm_df.empty:
                self._print_df_sample(tm_df)
                combined_tm_df = tm_df if combined_tm_df is None else pd.concat([combined_tm_df, tm_df])

            tm_link = await xds.generate_log_search_link(
                search_tenant,
                error_from,
                error_to,
                ['xtablemaster'],
                log_type='Error',
                search_string=self.account_name,
            )
            all_tm_links.append(tm_link)
            self._record_log_sample(
                f"TableMaster Error ({side_label}, {search_tenant})",
                tm_link, tm_df,
            )
            print(f"  TableMaster log search link: {tm_link}")

        # Use combined results for pattern matching
        xac_df = combined_xac_df if combined_xac_df is not None else pd.DataFrame()
        tm_df = combined_tm_df if combined_tm_df is not None else pd.DataFrame()
        evidence_links = all_xac_links + all_tm_links

        # A2b. Supplementary "now" verbose search for long-stuck failovers.
        # If both XACServer verbose and TableMaster error returned 0 at the
        # alert-anchored window, the account may still be actively retrying.
        # Verbose logs have ~2 day retention, so a recent window can capture
        # ongoing activity even when the original alert-time logs expired.
        # This is supplementary evidence only — it does NOT influence routing.
        if xac_df.empty and tm_df.empty:
            now = datetime.now(timezone.utc)
            now_from = now - timedelta(minutes=5)
            print(f"  Alert-time XDS returned 0 rows; checking current verbose ({now_from.isoformat()} -> {now.isoformat()})...")
            for search_tenant_now, side_label_now in search_tenants:
                if not search_tenant_now:
                    continue
                try:
                    now_result = await xds.search_log(
                        search_tenant_now,
                        now_from,
                        now,
                        ['xacserver'],
                        log_type='Verbose',
                        search_string=self.account_name,
                        top=20,
                    )
                    now_df = now_result.to_df()
                    print(f"  Current XACServer verbose on {search_tenant_now} ({side_label_now}): {len(now_df)} rows")
                    if not now_df.empty:
                        self._print_df_sample(now_df)
                        now_link = await xds.generate_log_search_link(
                            search_tenant_now, now_from, now,
                            ['xacserver'], log_type='Verbose',
                            search_string=self.account_name,
                        )
                        evidence_links.append(now_link)
                        print(f"  Current verbose link: {now_link}")
                        # Record as supplementary evidence (does not change routing)
                        sample_msgs = "; ".join(
                            str(row.get("message", ""))[:200]
                            for _, row in now_df.head(3).iterrows()
                        )
                        self.xds_evidence_summary += (
                            f" [Supplementary] Current XACServer verbose on "
                            f"{search_tenant_now}: {len(now_df)} rows. "
                            f"Samples: {sample_msgs}"
                        )
                except Exception as exc:
                    print(f"  WARNING: Current verbose search failed on {search_tenant_now}: {exc}")

        # A3. Classify the split failure pattern
        if not tm_df.empty:
            split_failures = tm_df[
                tm_df['message'].str.contains('Cannot split partition', na=False)
            ]
            llam_failures = split_failures[
                split_failures['message'].str.contains(
                    'Incompatible LLAM Stage', na=False
                )
            ]

            if not llam_failures.empty:
                sample_msg = str(llam_failures.iloc[0]['message'])[:300]
                print(f"  LLAM split block detected: {sample_msg}")
                self.xds_evidence_summary = (
                    f"TableMaster LLAM split block: {sample_msg}"
                )
                await self._transfer_incident(
                    tsg_input,
                    # TODO: Open Question — confirm exact ICM team path
                    target_tenant="Xstore",
                    target_team="StorageCRM",
                    reason=(
                        f"PrepareFailover stuck due to LLAM split block. "
                        f"Account: {self.account_name}, Tenant: {tsg_input.tenant_name}. "
                        f"TableMaster log: {sample_msg}"
                    ),
                    evidence_links=evidence_links,
                )
                return

            if not split_failures.empty:
                sample_msg = str(split_failures.iloc[0]['message'])[:300]
                print(f"  Non-LLAM split failure detected: {sample_msg}")
                self.xds_evidence_summary = (
                    f"TableMaster split failure (non-LLAM): {sample_msg}"
                )
                await self._transfer_incident(
                    tsg_input,
                    target_tenant="Xstore",
                    target_team="TableMaster",
                    reason=(
                        f"PrepareFailover stuck due to partition split failure. "
                        f"Account: {self.account_name}, Tenant: {tsg_input.tenant_name}. "
                        f"TableMaster log: {sample_msg}"
                    ),
                    evidence_links=evidence_links,
                )
                return

        # No recognizable TableMaster pattern — fall through to default
        print("  No known split failure pattern found in TableMaster logs")
        self.xds_evidence_summary = (
            f"PrepareFailover stuck but no known pattern in TableMaster error log. "
            f"XACServer verbose: {len(xac_df)} rows, TableMaster error: {len(tm_df)} rows."
        )
        await self._branch_e_default_escalation(
            tsg_input, extra_links=evidence_links
        )

    # ── Branch B — Both sides at PrepareFailover ───────────

    async def _branch_b_both_prepare_failover(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Diagnose both-PrepareFailover via Nephos.Account perf on Primary.

        Source TSG: when both sides are at PrepareFailover, search the
        Primary stamp's Nephos.Account perf log for PollFailover calls
        with GeoConfigOff.  If found → RA to XGeo DRI.
        """
        search_tenant = self.storage_tenant
        if not search_tenant:
            print("  No primary storage tenant resolved -- cannot search XDS logs")
            await self._branch_e_default_escalation(tsg_input)
            return

        event_time = self.alert_timestamp or tsg_input.incident_start_time_utc
        anchor_source = "alert_timestamp" if self.alert_timestamp else "incident_start_time_utc"
        print(f"  XDS time anchor: {event_time.isoformat()} (source={anchor_source})")
        perf_from = event_time - timedelta(minutes=2)
        perf_to = event_time + timedelta(minutes=2)
        print(f"  Searching Nephos.Account perf on {search_tenant} (Primary) for '{self.account_name}'...")
        print(f"    Window: {perf_from} -> {perf_to}, top=50")
        acct_result = await xds.search_log(
            search_tenant,
            perf_from,
            perf_to,
            ['nephos.account'],
            log_type='Perf',
            search_string=self.account_name,
            top=50,
        )
        acct_df = acct_result.to_df()
        print(f"  Nephos.Account perf results: {len(acct_df)} rows")
        if not acct_df.empty:
            self._print_df_sample(acct_df)

        acct_link = await xds.generate_log_search_link(
            search_tenant,
            perf_from,
            perf_to,
            ['nephos.account'],
            log_type='Perf',
            search_string=self.account_name,
        )
        print(f"  Nephos.Account log search link: {acct_link}")

        if acct_df.empty:
            print("  No Nephos.Account perf log entries found on Primary")
            self.xds_evidence_summary = (
                "Both sides PrepareFailover but no Nephos.Account perf logs on Primary."
            )
            await self._branch_e_default_escalation(
                tsg_input, extra_links=[acct_link]
            )
            return

        # B2. Find PollFailover calls and pick one to trace
        poll_entries = acct_df[
            acct_df['message'].str.contains('PollFailover', na=False)
        ]
        print(f"  PollFailover entries: {len(poll_entries)}")

        if poll_entries.empty:
            print("  No PollFailover entries in Nephos.Account perf log")
            self.xds_evidence_summary = (
                "Both sides PrepareFailover but no PollFailover entries in Primary perf log."
            )
            await self._branch_e_default_escalation(
                tsg_input, extra_links=[acct_link]
            )
            return

        sample_aid = str(poll_entries.iloc[0].get('activityId', ''))
        print(f"  Tracing PollFailover activity id: {sample_aid}")

        trace_result = await xds.search_by_activity_id(
            sample_aid, entry_level_only=True
        )
        trace_df = trace_result.to_df()
        print(f"  Activity trace results: {len(trace_df)} rows")
        if not trace_df.empty:
            self._print_df_sample(trace_df)

        # B3. Check for GeoConfigOff
        geo_off = trace_df[
            trace_df['message'].str.contains(r'GeoConfigOff', na=False)
        ]
        print(f"  GeoConfigOff entries: {len(geo_off)}")

        if not geo_off.empty:
            geo_msg = str(geo_off.iloc[0]['message'])[:300]
            print(f"  GeoConfigOff detected on Primary: {geo_msg}")
            self.xds_evidence_summary = f"Both PrepareFailover — GeoConfigOff on Primary: {geo_msg}"

            await self._escalate_ra_ximi(
                tsg_input,
                reason=(
                    f"Both sides at PrepareFailover with GeoConfigOff on Primary. "
                    f"Account: {self.account_name}, Tenant: {tsg_input.tenant_name}. "
                    f"Evidence: {geo_msg}"
                ),
                evidence_links=[acct_link],
            )
            return

        # No GeoConfigOff — default escalation
        print("  No GeoConfigOff pattern detected on Primary")
        self.xds_evidence_summary = (
            f"Both sides PrepareFailover, no GeoConfigOff on Primary. "
            f"Nephos.Account perf: {len(acct_df)} rows, PollFailover: {len(poll_entries)} entries."
        )
        await self._branch_e_default_escalation(
            tsg_input, extra_links=[acct_link]
        )

    # ── Branch C — FinalizeFailover (XFiles partition check) ────

    # GeoReplayerState codes (from Helper.ipynb)
    _LIVE_REPLAY_STATE = 102  # LiveReplay
    _LIVE_REPLAY_PAUSE_STATE = 103  # LiveReplayPause

    async def _branch_c_finalize_failover(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Check XFiles partition GeoReplayerState when both sides at FinalizeFailover.

        Escalation ladder (per TSG + user instruction):
        1. XDS API — ``x_table_get_partitions_stats`` → filter XFiles,
           check ``GeoReplayerState`` for LiveReplay (102) / LiveReplayPause (103).
        2. Kusto — ``GeoReplayerBlockedPartitions2`` on xstore cluster.
        3. Human fallback — provide full ``Get-XdsPartition`` command.
        """
        secondary_tenant = self.geo_pair_tenant or self.storage_tenant
        account = self.account_name or ""
        account_lower = account.lower()

        # ── Attempt 1: XDS API ──
        live_replay_partitions = await self._check_xfiles_partition_via_api(
            secondary_tenant, account_lower
        )

        if live_replay_partitions is not None:
            # API succeeded — act on the result
            if live_replay_partitions:
                await self._handle_live_replay_found(
                    tsg_input, secondary_tenant, live_replay_partitions, source="XDS API"
                )
                return
            # API worked but no LiveReplay partitions found
            print("  XDS API: no LiveReplay XFiles partitions found")
            self.xds_evidence_summary = (
                f"Both FinalizeFailover — XDS API checked {secondary_tenant}, "
                f"no LiveReplay XFiles partitions for {account}."
            )
            await self._branch_e_default_escalation(tsg_input)
            return

        # ── Attempt 2: Kusto GeoReplayerBlockedPartitions2 ──
        print("  XDS API failed — falling back to Kusto")
        kusto_partitions = await self._check_xfiles_partition_via_kusto(
            secondary_tenant, account_lower
        )

        if kusto_partitions is not None:
            if kusto_partitions:
                await self._handle_live_replay_found(
                    tsg_input, secondary_tenant, kusto_partitions, source="Kusto"
                )
                return
            print("  Kusto: no LiveReplay XFiles partitions found")
            self.xds_evidence_summary = (
                f"Both FinalizeFailover — Kusto checked {secondary_tenant}, "
                f"no LiveReplay XFiles partitions for {account}."
            )
            await self._branch_e_default_escalation(tsg_input)
            return

        # ── Attempt 3: Human fallback with full command ──
        print("  Both XDS API and Kusto failed — escalating to human with full command")
        await self._branch_c_human_fallback(tsg_input, secondary_tenant, account)

    async def _check_xfiles_partition_via_api(
        self, tenant: str, account_lower: str
    ) -> list[dict] | None:
        """Query XDS x_table_get_partitions_stats for XFiles LiveReplay partitions.

        Returns a list of dicts (one per matching partition) on success,
        or ``None`` if the API call fails.
        """
        try:
            from xds_client import XTableApi, ApiClient
            import datetime as _dt

            client = ApiClient()
            await client.connect_tenant(tenant)
            xtable = XTableApi(client)

            live_replay = []
            page = 0
            max_pages = 50  # safety limit
            print(f"  Querying XDS partition stats on {tenant}...")

            while page < max_pages:
                result = await xtable.x_table_get_partitions_stats(
                    page_number=page,
                    if_modified_since=_dt.datetime.min,
                )
                col_names = [c.name for c in result.schema.columns]
                msn_idx = col_names.index("MetadataStreamName")
                geo_idx = col_names.index("GeoReplayerState")
                low_idx = col_names.index("LowKey")
                sm_idx = col_names.index("StateMachineState")

                for row in result.rows:
                    msn = str(row[msn_idx]).lower()
                    if "xfiles!" not in msn:
                        continue
                    # Filter by account name in LowKey
                    low_key = str(row[low_idx]).lower()
                    if account_lower and account_lower not in low_key:
                        continue
                    geo_state = int(row[geo_idx]) if row[geo_idx] else 0
                    if geo_state in (
                        self._LIVE_REPLAY_STATE,
                        self._LIVE_REPLAY_PAUSE_STATE,
                    ):
                        live_replay.append({
                            "MetadataStreamName": str(row[msn_idx]),
                            "GeoReplayerState": geo_state,
                            "StateMachineState": str(row[sm_idx]),
                            "LowKey": str(row[low_idx]),
                        })

                print(f"    Page {page}: {len(result.rows)} partitions, "
                      f"LiveReplay so far: {len(live_replay)}")

                if result.continuation_key is None:
                    break
                page += 1

            print(f"  XDS API complete: {len(live_replay)} LiveReplay XFiles partitions")
            return live_replay
        except Exception as exc:
            print(f"  XDS API error: {exc}")
            return None

    async def _check_xfiles_partition_via_kusto(
        self, tenant: str, account_lower: str
    ) -> list[dict] | None:
        """Query GeoReplayerBlockedPartitions2 Kusto table for LiveReplay.

        Returns a list of dicts on success, or ``None`` on failure.
        """
        cluster = "https://xstore.kusto.windows.net"
        database = "xstore"
        account_filter = f'| where LowKey contains "{account_lower}"' if account_lower else ""
        kql = (
            f'GeoReplayerBlockedPartitions2\n'
            f'| where Tenant == "{tenant}"\n'
            f'| where MetadataStreamName contains "xfiles!"\n'
            f'{account_filter}\n'
            f'| where GeoReplayerState in (102, 103)\n'
            f'| project MetadataStreamName, GeoReplayerState, LowKey\n'
            f'| take 100'
        )
        try:
            print(f"  Querying Kusto GeoReplayerBlockedPartitions2 for {tenant}...")
            result = await kusto.query(cluster, database, kql)
            df = result.to_df()
            print(f"  Kusto result: {len(df)} rows")
            if df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as exc:
            print(f"  Kusto query error: {exc}")
            return None

    async def _handle_live_replay_found(
        self,
        tsg_input: FailoverPendingTransactionInput,
        tenant: str,
        partitions: list[dict],
        source: str,
    ) -> None:
        """Transfer incident to XStore\\SMB when LiveReplay partitions exist."""
        partition_summary = "; ".join(
            f"{p.get('MetadataStreamName', '?')[:80]} state={p.get('GeoReplayerState')}"
            for p in partitions[:5]
        )
        if len(partitions) > 5:
            partition_summary += f" ... and {len(partitions) - 5} more"

        print(f"  {source}: {len(partitions)} LiveReplay XFiles partitions found")
        self.xds_evidence_summary = (
            f"Both FinalizeFailover — LiveReplay XFiles partitions on {tenant} "
            f"({source}): {partition_summary}"
        )

        await self._transfer_incident(
            tsg_input,
            target_tenant="XStore",
            target_team="SMB",
            reason=(
                f"FinalizeFailover — {len(partitions)} XFiles partitions in LiveReplay "
                f"on {tenant} (detected via {source}). "
                f"Account: {self.account_name}. "
                f"Evidence: {partition_summary}"
            ),
        )

    async def _branch_c_human_fallback(
        self,
        tsg_input: FailoverPendingTransactionInput,
        secondary_tenant: str,
        account: str,
    ) -> None:
        """Escalate to human with full Get-XdsPartition command and partial evidence."""
        instructions = (
            f"Both sides at FinalizeFailover — automated XFiles check failed.\n"
            f"XDS API and Kusto both unavailable/errored.\n"
            f"\n"
            f"Manual command to run in XScript / XDS console:\n"
            f"  Get-XdsPartition -Tenant {secondary_tenant} -Table XFiles "
            f"-Account {account}\n"
            f"\n"
            f"Look for partitions whose StateMachineState contains 'GeoReplay:LiveReplay'\n"
            f"or GeoReplayerState = 102 (LiveReplay) / 103 (LiveReplayPause).\n"
            f"  • If found → transfer incident to XStore\\SMB team.\n"
            f"  • If not found → escalate to XGeo DRI (ximi@microsoft.com).\n"
        )

        self.xds_evidence_summary = (
            f"Both FinalizeFailover — XDS API and Kusto failed on {secondary_tenant}. "
            f"Manual Get-XdsPartition check required."
        )

        summary = self._build_evidence_summary(tsg_input)
        summary += f"\nManual step required:\n{instructions}\n"

        if self.dry_run:
            print(f"  [DRY-RUN] Would post evidence + instructions to ICM {tsg_input.incident_id}")
            print(f"  [DRY-RUN] Evidence summary:\n{summary}")
            print(f"  [DRY-RUN] ManualActionRequired would be raised")
            return

        html_summary = self._build_evidence_summary_html(
            tsg_input,
            extra_html=(
                "<h3>Manual step required</h3>"
                f"<pre>{self._html_escape(instructions)}</pre>"
            ),
        )
        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False
        )
        await incident.add_description(html_summary, is_html=True)
        self._evidence_posted_to_icm = True
        print(f"  Evidence + instructions posted to ICM {tsg_input.incident_id}")

        print("=" * 60)
        print("MANUAL ACTION REQUIRED: XFiles partition state check")
        print(instructions)
        print("=" * 60)
        raise ManualActionRequired(
            f"FinalizeFailover — run Get-XdsPartition on {secondary_tenant} "
            f"for account {account} and check for GeoReplay:LiveReplay.\n"
            f"Both XDS API and Kusto were unavailable."
        )

    # ── Branch D — DnsSwitch (XACServer 0x830a382d) ──────────

    async def _branch_d_dns_switch(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Diagnose DnsSwitch block via XACServer verbose on Secondary.

        Source TSG: when both sides are at DnsSwitch, search the
        secondary stamp's XACServer verbose log for error code
        ``0x830a382d``.  If found → RA to XGeo DRI.
        """
        search_tenant = self.geo_pair_tenant or self.storage_tenant
        if not search_tenant:
            print("  No secondary/storage tenant resolved -- cannot search XDS logs")
            await self._branch_e_default_escalation(tsg_input)
            return

        event_time = self.alert_timestamp or tsg_input.incident_start_time_utc
        anchor_source = "alert_timestamp" if self.alert_timestamp else "incident_start_time_utc"
        print(f"  XDS time anchor: {event_time.isoformat()} (source={anchor_source})")
        search_from = event_time - timedelta(minutes=15)
        search_to = event_time + timedelta(minutes=15)

        # D1. Search XACServer verbose on Secondary for 0x830a382d
        print(f"  Searching XACServer verbose on {search_tenant} (Secondary) for '0x830a382d'...")
        print(f"    Window: {search_from} -> {search_to}, top=50")
        xac_result = await xds.search_log(
            search_tenant,
            search_from,
            search_to,
            ['xacserver'],
            log_type='Verbose',
            search_string='0x830a382d',
            top=50,
        )
        xac_df = xac_result.to_df()
        xac_link = await xds.generate_log_search_link(
            search_tenant,
            search_from,
            search_to,
            ['xacserver'],
            log_type='Verbose',
            search_string='0x830a382d',
        )
        print(f"  XACServer verbose results: {len(xac_df)} rows")
        print(f"  Link: {xac_link}")
        if not xac_df.empty:
            self._print_df_sample(xac_df)

        if not xac_df.empty:
            sample_msg = str(xac_df.iloc[0].get('message', ''))[:300]
            print(f"  0x830a382d error detected on Secondary: {sample_msg}")
            self.xds_evidence_summary = (
                f"DnsSwitch — 0x830a382d on Secondary: {sample_msg}"
            )
            await self._escalate_ra_ximi(
                tsg_input,
                reason=(
                    f"DnsSwitch stuck with 0x830a382d on Secondary. "
                    f"Account: {self.account_name}, Tenant: {tsg_input.tenant_name}. "
                    f"Evidence: {sample_msg}"
                ),
                evidence_links=[xac_link],
            )
            return

        # No 0x830a382d found — default escalation
        print("  No 0x830a382d pattern found on Secondary")
        self.xds_evidence_summary = (
            f"DnsSwitch stuck but no 0x830a382d on Secondary XACServer verbose."
        )
        await self._branch_e_default_escalation(
            tsg_input, extra_links=[xac_link]
        )

    # ── Branch E — Default escalation ────────────────────────

    async def _branch_e_default_escalation(
        self, tsg_input: FailoverPendingTransactionInput,
        extra_links: list[str] = None,
    ) -> None:
        """Escalate to XGeo DRI when no known-issue pattern matches."""
        await self._escalate_ra_ximi(
            tsg_input,
            reason=(
                f"FailoverPendingTransaction — unknown stuck pattern. "
                f"Primary={self.primary_stage}, Secondary={self.secondary_stage}. "
                f"Stuck: {self.stuck_location}/{self.stuck_stage}. "
                f"Account: {self.account_name}, Tenant: {tsg_input.tenant_name}. "
                f"Operation: {self.operation_id}."
            ),
            evidence_links=extra_links,
        )

    # ── Helper: Transfer ICM to a team ───────────────────────

    async def _transfer_incident(
        self,
        tsg_input: FailoverPendingTransactionInput,
        target_tenant: str,
        target_team: str,
        reason: str,
        evidence_links: list[str] = None,
    ) -> None:
        """Add evidence and transfer incident to the target team."""
        self.mitigation_status = "Transferred"
        self.mitigation_detail = f"Transferred to {target_tenant}/{target_team}: {reason}"

        summary = self._build_evidence_summary(tsg_input, evidence_links)
        summary += f"\nAction: Transferring to {target_tenant}/{target_team}\n"
        summary += f"Reason: {reason}\n"

        if self.dry_run:
            print(f"  [DRY-RUN] Would post evidence to ICM {tsg_input.incident_id}")
            print(f"  [DRY-RUN] Would transfer to {target_tenant}/{target_team}")
            print(f"  [DRY-RUN] Evidence summary:\n{summary}")
            return

        html_summary = self._build_evidence_summary_html(
            tsg_input, evidence_links,
            extra_html=(
                f"<h3>Action</h3><p>Transferring to <b>{self._html_escape(target_tenant)}/"
                f"{self._html_escape(target_team)}</b></p>"
                f"<p><b>Reason:</b> {self._html_escape(reason)}</p>"
            ),
        )
        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False
        )
        await incident.add_description(html_summary, is_html=True)
        print(f"  Evidence posted to ICM {tsg_input.incident_id}")

        # APPROVAL_GATE: ICM transfer is a mutating action
        print("=" * 60)
        print(f"APPROVAL REQUIRED: Transfer incident to {target_tenant}/{target_team}")
        print(f"  Reason: {reason}")
        print("=" * 60)
        await incident.transfer(
            tenant=target_tenant,
            team=target_team,
            reason=reason,
        )
        print(f"  ICM {tsg_input.incident_id}: transferred to {target_tenant}/{target_team}")

    # ── Helper: Escalate RA to ximi ──────────────────────────

    @staticmethod
    def _select_escalation_target(now: datetime | None = None) -> tuple[str, str, str]:
        """Pick the escalation target based on the current working-hour overlap.

        Per the source TSG, the default-escalation route depends on who is
        on shift right now:

        * **China working hours** (Asia/Shanghai, Mon-Fri 09:00-18:00) →
          email ``ximi@microsoft.com``.
        * **Otherwise** (Redmond working hours or after-hours globally) →
          *RA XGeo DRI* in ICM (no dedicated email; the on-call rotation
          picks the ticket up via Request Assistant).

        Returns ``(target_label, route_description, action_keyword)``:

        * ``target_label`` — short identifier for logs / summary
          (``"ximi@microsoft.com"`` or ``"XGeo DRI (RA in ICM)"``).
        * ``route_description`` — human-readable phrase used in the ICM
          description.
        * ``action_keyword`` — internal key (``"ximi"`` or ``"xgeo"``)
          used by callers that need to branch on the chosen route.
        """
        from zoneinfo import ZoneInfo

        now = now or datetime.now(timezone.utc)
        cn_now = now.astimezone(ZoneInfo("Asia/Shanghai"))
        if cn_now.weekday() < 5 and 9 <= cn_now.hour < 18:
            return (
                "ximi@microsoft.com",
                "Email ximi@microsoft.com (China working hours)",
                "ximi",
            )
        return (
            "XGeo DRI (RA in ICM)",
            "RA XGeo DRI in ICM (Redmond working hours / after-hours global)",
            "xgeo",
        )

    async def _escalate_ra_ximi(
        self,
        tsg_input: FailoverPendingTransactionInput,
        reason: str,
        evidence_links: list[str] = None,
    ) -> None:
        """Add evidence and escalate to XGeo DRI / ximi based on working hours.

        The route is decided by ``_select_escalation_target`` at the moment
        of the actual escalation:

        * China working hours → email ``ximi@microsoft.com``.
        * Otherwise          → RA XGeo DRI via ICM.

        When ``self._defer_escalation`` is True (set during the per-candidate
        loop in ``_run``), this method only records the escalation intent and
        returns.  The actual ICM mutation is performed once at the end of the
        loop by ``_perform_deferred_escalation`` so we exhaust every sampled
        account before "giving up".
        """
        if self._defer_escalation:
            self.mitigation_status = "EscalationDeferred"
            self.mitigation_detail = f"Escalation deferred (will retry remaining candidates): {reason}"
            self._deferred_escalations.append(
                {
                    "account_name": self.account_name,
                    "operation_id": self.operation_id,
                    "stuck_location": self.stuck_location,
                    "stuck_stage": self.stuck_stage,
                    "primary_stage": self.primary_stage,
                    "secondary_stage": self.secondary_stage,
                    "reason": reason,
                    "evidence_links": list(evidence_links or []),
                    "xds_evidence_summary": self.xds_evidence_summary,
                }
            )
            print(
                "  Escalation deferred for this candidate; will revisit after "
                "all sampled accounts are exhausted."
            )
            return

        target_label, route_description, _ = self._select_escalation_target()
        self.mitigation_status = "Escalated"
        self.mitigation_detail = f"Escalated via {route_description}: {reason}"

        summary = self._build_evidence_summary(tsg_input, evidence_links)
        summary += f"\nAction: Escalating to XGeo DRI ({target_label})\n"
        summary += f"Route: {route_description}\n"
        summary += f"Reason: {reason}\n"

        if self.dry_run:
            print(f"  [DRY-RUN] Would post evidence to ICM {tsg_input.incident_id}")
            print(f"  [DRY-RUN] Would escalate to: {target_label}")
            print(f"  [DRY-RUN] Route: {route_description}")
            print(f"  [DRY-RUN] Evidence summary:\n{summary}")
            print(f"  [DRY-RUN] ManualActionRequired would be raised: {target_label} — {reason}")
            return

        html_summary = self._build_evidence_summary_html(
            tsg_input, evidence_links,
            extra_html=(
                f"<h3>Action</h3><p>Escalating to XGeo DRI: <b>{self._html_escape(target_label)}</b></p>"
                f"<p><b>Route:</b> {self._html_escape(route_description)}</p>"
                f"<p><b>Reason:</b> {self._html_escape(reason)}</p>"
            ),
        )
        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False
        )
        await incident.add_description(html_summary, is_html=True)
        self._evidence_posted_to_icm = True
        print(f"  Evidence posted to ICM {tsg_input.incident_id}")

        print("=" * 60)
        print("MANUAL ACTION REQUIRED: Escalate to XGeo DRI")
        print(f"  Route: {route_description}")
        print(f"  Target: {target_label}")
        print(f"  Stuck: {self.stuck_location} / {self.stuck_stage}")
        print(f"  Reason: {reason}")
        print("  Escalation summary has been added to the incident.")
        print("=" * 60)
        raise ManualActionRequired(
            f"Escalate to {target_label} ({route_description}) — {reason}"
        )

    async def _perform_deferred_escalation(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Escalate once with combined evidence from every sampled candidate."""
        if not self._deferred_escalations:
            return

        print("=" * 60)
        print(
            f"All {len(self.candidate_failovers)} sampled candidate(s) exhausted "
            f"with no actionable diagnosis; performing combined escalation."
        )
        print("=" * 60)

        combined_links: list[str] = []
        seen_links: set[str] = set()
        reason_lines: list[str] = []
        for idx, item in enumerate(self._deferred_escalations, start=1):
            reason_lines.append(
                f"  {idx}. account={item['account_name']}, operation={item['operation_id']}, "
                f"stuck={item['stuck_location']}/{item['stuck_stage']}: {item['reason']}"
            )
            for link in item.get("evidence_links", []):
                if link and link not in seen_links:
                    seen_links.add(link)
                    combined_links.append(link)

        combined_reason = (
            f"FailoverPendingTransaction — no known-issue pattern matched after "
            f"investigating {len(self._deferred_escalations)} sampled account(s):\n"
            + "\n".join(reason_lines)
        )

        # Pivot the active state to the most recently investigated candidate
        # (last in deferred list) so the escalation summary is grounded in a
        # concrete account.
        last = self._deferred_escalations[-1]
        self.account_name = last["account_name"]
        self.operation_id = last["operation_id"]
        self.stuck_location = last["stuck_location"]
        self.stuck_stage = last["stuck_stage"]
        self.primary_stage = last["primary_stage"]
        self.secondary_stage = last["secondary_stage"]

        try:
            await self._escalate_ra_ximi(
                tsg_input,
                reason=combined_reason,
                evidence_links=combined_links,
            )
        finally:
            # Promote per-candidate "EscalationDeferred" status to "Escalated"
            # (and refresh the detail) so the final TSG output and per-account
            # summary reflect the action that was actually taken.  The actual
            # ximi-vs-XGeo-DRI route was chosen inside the combined
            # _escalate_ra_ximi call above and is already recorded in
            # self.mitigation_detail; we mirror it onto each candidate here.
            combined_detail = self.mitigation_detail
            for summary in self.account_investigation_summaries:
                if summary.get("mitigation_status") == "EscalationDeferred":
                    summary["mitigation_status"] = "Escalated"
                    summary["mitigation_detail"] = (
                        f"Combined escalation after exhausting "
                        f"{len(self.candidate_failovers)} sampled account(s) | "
                        f"{combined_detail}"
                    )

    # ── Helper: Build evidence summary ───────────────────────

    def _build_evidence_summary(
        self,
        tsg_input: FailoverPendingTransactionInput,
        extra_links: list[str] = None,
    ) -> str:
        """Build a text block with all triage evidence."""
        all_links = list(self.dgrep_links)
        if extra_links:
            all_links.extend(extra_links)

        summary = (
            f"FailoverPendingTransaction automated triage:\n"
            f"  Incident: {tsg_input.incident_id}\n"
            f"  Tenant: {tsg_input.tenant_name}\n"
            f"  Expected stuck from title: {tsg_input.expected_stuck_location}Stuck.{tsg_input.expected_stuck_stage}\n"
            f"  Account: {self.account_name}\n"
            f"  Operation ID: {self.operation_id}\n"
            f"  Primary stage: {self.primary_stage}\n"
            f"  Secondary stage: {self.secondary_stage}\n"
            f"  Stage source: {self.stage_source}\n"
            f"  Stuck location: {self.stuck_location}\n"
            f"  Stuck stage: {self.stuck_stage}\n"
            f"  XDS findings: {self.xds_evidence_summary}\n"
            f"  Sampled accounts: {len(self.candidate_failovers)}\n"
            f"  Evidence links:\n"
        )
        for link in all_links:
            summary += f"    - {link}\n"
        return summary

    @staticmethod
    def _html_escape(s: Any) -> str:
        import html as _html

        return _html.escape("" if s is None else str(s))

    def _build_evidence_summary_html(
        self,
        tsg_input: FailoverPendingTransactionInput,
        extra_links: list[str] = None,
        extra_html: str = "",
    ) -> str:
        """Build the HTML version of the triage evidence for ICM.

        Includes a sample-rows table for every captured DGrep / XDS query so
        the on-call doesn't have to click through every link to see what we
        found.  Long ``message`` columns were already truncated when the
        sample was recorded.
        """
        e = self._html_escape
        all_links = list(self.dgrep_links)
        if extra_links:
            all_links.extend(extra_links)

        title_stuck = (
            f"{tsg_input.expected_stuck_location}Stuck.{tsg_input.expected_stuck_stage}"
        )

        rows = [
            ("Incident", tsg_input.incident_id),
            ("Tenant", tsg_input.tenant_name),
            ("Expected stuck (from title)", title_stuck),
            ("Account", self.account_name),
            ("Operation ID", self.operation_id),
            ("Primary stage", self.primary_stage),
            ("Secondary stage", self.secondary_stage),
            ("Stage source", self.stage_source),
            ("Stuck location / stage", f"{self.stuck_location} / {self.stuck_stage}"),
            ("XDS findings", self.xds_evidence_summary),
            ("Sampled accounts", len(self.candidate_failovers)),
            ("Mitigation status", self.mitigation_status),
            ("Mitigation detail", self.mitigation_detail),
        ]
        meta_rows = "".join(
            f"<tr><th align='left'>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in rows
        )

        links_html = (
            "<ul>"
            + "".join(
                f"<li><a href='{e(link)}'>{e(link)}</a></li>"
                for link in all_links
                if link
            )
            + "</ul>"
        ) if all_links else "<p><em>(none)</em></p>"

        candidates_html = ""
        if self.account_investigation_summaries:
            header = (
                "<tr><th>#</th><th>Account</th><th>Operation</th>"
                "<th>Matched stuck</th><th>Completed</th>"
                "<th>Stuck</th><th>Mitigation</th></tr>"
            )
            body = "".join(
                f"<tr><td>{i}</td><td>{e(s.get('account_name',''))}</td>"
                f"<td>{e(s.get('operation_id',''))}</td>"
                f"<td>{e(s.get('matched_stuck','') or 'Unknown')}</td>"
                f"<td>{e(s.get('is_completed','False'))}</td>"
                f"<td>{e(s.get('stuck_location',''))}/{e(s.get('stuck_stage',''))}</td>"
                f"<td>{e(s.get('mitigation_status',''))}</td></tr>"
                for i, s in enumerate(self.account_investigation_summaries, start=1)
            )
            candidates_html = (
                "<h3>Per-account investigation</h3>"
                f"<table border='1' cellpadding='4' cellspacing='0'>{header}{body}</table>"
            )

        samples_html = ""
        if self.evidence_log_samples:
            parts = ["<h3>Sample logs</h3>"]
            for sample in self.evidence_log_samples:
                label = e(sample.get("label", ""))
                link = sample.get("link", "")
                total = sample.get("total_rows", 0)
                shown = sample.get("sample_rows", 0)
                link_html = (
                    f" — <a href='{e(link)}'>open in log search</a>" if link else ""
                )
                parts.append(
                    f"<h4>{label} (showing {shown} of {total} rows){link_html}</h4>"
                )
                if sample.get("html"):
                    parts.append(sample["html"])
                else:
                    parts.append("<p><em>No rows.</em></p>")
            samples_html = "".join(parts)

        return (
            "<h2>FailoverPendingTransaction automated triage</h2>"
            f"<table border='1' cellpadding='4' cellspacing='0'>{meta_rows}</table>"
            "<h3>Evidence links</h3>"
            f"{links_html}"
            f"{candidates_html}"
            f"{samples_html}"
            f"{extra_html or ''}"
        )

    # ── Step 5 — Update incident ─────────────────────────────

    async def _step_5_update_incident(
        self, tsg_input: FailoverPendingTransactionInput
    ) -> None:
        """Add triage evidence to incident and close triage loop.

        Coding ability: icm-get-incident
        AUTOMATABLE: Yes
        """
        evidence = (
            f"Automated triage results:\n"
            f"  Expected stuck from title: {tsg_input.expected_stuck_location}Stuck.{tsg_input.expected_stuck_stage}\n"
            f"  Sampled accounts investigated: {len(self.account_investigation_summaries)}\n"
            f"  Account: {self.account_name}\n"
            f"  Operation ID: {self.operation_id}\n"
            f"  Failover completed: {self.is_completed}\n"
            f"  Primary stage: {self.primary_stage}\n"
            f"  Secondary stage: {self.secondary_stage}\n"
            f"  Stage source: {self.stage_source}\n"
            f"  Stuck location: {self.stuck_location}\n"
            f"  Stuck stage: {self.stuck_stage}\n"
            f"  Mitigation status: {self.mitigation_status}\n"
            f"  Mitigation detail: {self.mitigation_detail}\n"
            f"  XDS evidence: {self.xds_evidence_summary}\n"
            f"  DGrep evidence links:\n"
        )
        if self.account_investigation_summaries:
            evidence += "  Per-account investigation summary:\n"
            for idx, summary in enumerate(self.account_investigation_summaries, start=1):
                evidence += (
                    f"    {idx}. account={summary.get('account_name', '')}, "
                    f"operation={summary.get('operation_id', '')}, "
                    f"matched_stuck={summary.get('matched_stuck', '') or 'Unknown'}, "
                    f"completed={summary.get('is_completed', 'False')}, "
                    f"stuck={summary.get('stuck_location', '')}/{summary.get('stuck_stage', '')}, "
                    f"mitigation={summary.get('mitigation_status', '')}\n"
                )

        for link in self.dgrep_links:
            evidence += f"    - {link}\n"

        if self.dry_run:
            if self._evidence_posted_to_icm:
                print(
                    f"  [DRY-RUN] Skipping triage evidence post to ICM "
                    f"{tsg_input.incident_id} (action path already would have posted)"
                )
            else:
                print(f"  [DRY-RUN] Would post triage evidence to ICM {tsg_input.incident_id}")
                print(f"  [DRY-RUN] Evidence:\n{evidence}")
            if self.is_completed:
                print(f"  [DRY-RUN] Would auto-mitigate ICM {tsg_input.incident_id}")
            return

        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False
        )
        # Skip duplicate description: any action path (transfer / escalate /
        # branch_c human fallback) has already posted a body derived from the
        # same _build_evidence_summary_html.  Re-posting it would just create
        # noise on the incident.  Step 5's only remaining job in that case is
        # the auto-mitigate guard below.
        if self._evidence_posted_to_icm:
            print(
                f"  ICM {tsg_input.incident_id}: skipping duplicate triage description "
                f"(action path already posted full evidence summary)"
            )
        else:
            html_evidence = self._build_evidence_summary_html(
                tsg_input,
                extra_html=(
                    f"<h3>Failover completion</h3>"
                    f"<p><b>Failover completed:</b> {self._html_escape(self.is_completed)}</p>"
                ),
            )
            await incident.add_description(html_evidence, is_html=True)
            self._evidence_posted_to_icm = True
            print(f"  ICM {tsg_input.incident_id}: triage evidence posted")

        # Auto-mitigate only if failover confirmed complete
        # If transferred or escalated, leave incident open for owning team
        if self.is_completed:
            try:
                await incident.mitigate(
                    reason="Failover completed -- confirmed via AccountFailoverEvent"
                )
                print(f"  ICM {tsg_input.incident_id}: mitigated")
            except Exception as e:
                print(f"  ICM {tsg_input.incident_id}: mitigate failed (may already be mitigated): {e}")
