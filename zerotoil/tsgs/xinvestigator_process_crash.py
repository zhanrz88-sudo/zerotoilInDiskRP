"""XInvestigator Process Crash TSG.

Generated from: zero-toil/tsgs/xinvestigator-process-crash/xinvestigator-process-crash.md
Source: User-provided TSG content (XInvestigator Process Crash TSG)
Monitor ID: "Role Process Crash"

Triage and mitigate incidents where an XInvestigator worker role
(e.g., AutoAnalysisWorkerRole) crashes frequently — typically 16+ times
in 60 minutes.  Queries DGrep for crash logs, classifies the error
pattern, checks for recent deployments, and routes to the appropriate
mitigation path (revert deployment, skip failing smoke test, or
escalate to service owner).
"""

import datetime
import re
from typing import Any, Optional

from pydantic import ConfigDict
from xportal import dgrep, icm, kusto

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput


class ManualActionRequired(Exception):
    """Raised when a TSG step requires human intervention."""


# ── Input / Output models ───────────────────────────────────


class XinvestigatorProcessCrashInput(TsgInput):
    """Input for XInvestigator Process Crash TSG.

    Entry-level TSG: incident_id comes from TsgInput base.
    Additional fields are extracted from the ICM incident title/time.
    """

    model_config = ConfigDict(extra="forbid")

    process_name: str
    tenant_name: str
    incident_time: datetime.datetime


class XinvestigatorProcessCrashOutput(TsgOutput):
    """Output from XInvestigator Process Crash TSG."""

    model_config = ConfigDict(extra="forbid")

    error_classification: str = ""
    deployment_found: bool = False
    mitigation_action: str = ""
    root_cause_summary: str = ""


# ── Static mappings ─────────────────────────────────────────

# Process name prefix → (service name, ADO pipeline definition ID)
_PIPELINE_MAP: dict[str, tuple[str, int]] = {
    "AutoAnalysis": ("AutoAnalysis", 395813),
    "AutoTsg": ("AutoTsg", 392091),
    "XD": ("XD", 396535),
    "XlivesiteCollector": ("XlivesiteCollector", 396539),
    "XPortalDataProvider": ("XPortal DataProvider", 396537),
    "XJPLTrigger": ("XJPL Trigger", 396381),
    "XPortal": ("XPortal", 396578),
    "AcisExtension": ("ACIS Extension", 399283),
}

# Smoke test patterns that indicate smoke test failure
_SMOKE_TEST_KEYWORDS = [
    "SmokeTest",
    "AASmokeTests",
    "ParallelTest",
]

_AUTH_ERROR_PATTERNS = [
    "403-Forbidden",
    "Unauthorized",
    "KustoRequestDeniedException",
    "CertificateExpiredException",
]

_NON_SMOKE_EXCEPTION_TYPES = [
    "OutOfMemoryException",
    "StackOverflowException",
    "NullReferenceException",
    "TimeoutException",
    "SocketException",
]

_KNOWN_TEST_NAMES = [
    "RunKustoAccessProductionTest",
    "RunKustoAccessNationalCloudTest",
    "RunXdsAccessTest",
    "RunXlsAccessTest",
    "RunMdmAccessTest",
    "RunStorageAccessTest",
    "RunServiceBusTest",
    "RunIcmUpdateIncidentTest",
    "RunOnCallClientTest",
    "RunXLivesiteDCLoadTest",
    "RunMdsAccessTest",
    "RunRsrpAccessTest",
    "RunHealthServiceAccessTest",
]

# Tests that must NEVER be skipped
_NEVER_SKIP_TESTS = {"RunServiceBusTest"}

# Code-bug exception types that warrant deployment revert, not test skip
_CODE_BUG_EXCEPTIONS = {
    "NullReferenceException",
    "StackOverflowException",
    "OutOfMemoryException",
}


# ── TSG class ────────────────────────────────────────────────


class XinvestigatorProcessCrash(TsgBase):
    """Triage XInvestigator Process Crash incidents.

    Steps:
        1. Query crash logs from DGrep
        2. Analyze error pattern
        3. Check for recent deployments
        4. Route to mitigation
        5. Document and follow up
    """

    input_type = XinvestigatorProcessCrashInput
    output_type = XinvestigatorProcessCrashOutput

    # intermediate state
    crash_logs: Optional[Any] = None  # DataFrame
    dgrep_link: str = ""
    log_count: int = 0
    error_classification: str = ""
    exception_type: str = ""
    failing_test_name: str = ""
    external_service: str = ""
    error_code: str = ""
    error_summary: str = ""
    deployment_found: bool = False
    pipeline_name: str = ""
    pipeline_url: str = ""
    last_deployment_time: Optional[datetime.datetime] = None
    mitigation_action: str = ""
    mitigation_details: str = ""
    root_cause_summary: str = ""

    # ── Incident title pattern ───────────────────────────────
    # Example title: "Role Process Crash: AutoAnalysisWorkerRole in
    #   AutoAnalysisCSESWestCentralUS crashed 16 times in 60 minutes"
    _TITLE_PATTERN = re.compile(
        r"Role\s+Process\s+Crash[:\s]+(\S+)\s+in\s+(\S+)",
        re.IGNORECASE,
    )

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> XinvestigatorProcessCrashInput:
        """Extract process_name, tenant_name, and incident_time from ICM."""
        title = incident.Title or ""

        match = self._TITLE_PATTERN.search(title)
        process_name = match.group(1) if match else ""
        tenant_name = match.group(2) if match else ""

        # Fallback: scan descriptions if title didn't match
        if not process_name or not tenant_name:
            descriptions = getattr(incident, "Descriptions", None) or []
            for desc in descriptions:
                text = getattr(desc, "Text", None) or ""
                m = self._TITLE_PATTERN.search(text)
                if m:
                    process_name = process_name or m.group(1)
                    tenant_name = tenant_name or m.group(2)
                    break

        if not process_name:
            raise ValueError(
                f"Could not extract process_name from incident {incident_id} "
                f"title: {title!r}"
            )
        if not tenant_name:
            raise ValueError(
                f"Could not extract tenant_name from incident {incident_id} "
                f"title: {title!r}"
            )

        incident_time: datetime.datetime = incident.CreateDate

        print(f"  Extracted from incident {incident_id}:")
        print(f"    process_name  = {process_name}")
        print(f"    tenant_name   = {tenant_name}")
        print(f"    incident_time = {incident_time}")

        return XinvestigatorProcessCrashInput(
            incident_id=incident_id,
            process_name=process_name,
            tenant_name=tenant_name,
            incident_time=incident_time,
        )

    async def _run(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> XinvestigatorProcessCrashOutput:
        """Execute all TSG steps in sequence."""
        await self.run_step(self._step_1_query_crash_logs, tsg_input)
        await self.run_step(self._step_2_analyze_error_pattern, tsg_input)
        await self.run_step(self._step_3_check_deployment, tsg_input)
        await self.run_step(self._step_4_route_mitigation, tsg_input)
        await self.run_step(self._step_5_document_followup, tsg_input)

        return XinvestigatorProcessCrashOutput(
            error_classification=self.error_classification,
            deployment_found=self.deployment_found,
            mitigation_action=self.mitigation_action,
            root_cause_summary=self.root_cause_summary,
        )

    # ── Step 1: Query crash logs from DGrep ──────────────────

    async def _step_1_query_crash_logs(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Query DGrep for unhandled exception logs."""
        incident_time = tsg_input.incident_time
        process_name = tsg_input.process_name
        tenant_name = tsg_input.tenant_name

        scope_conditions = {
            "Role": process_name,
            "Tenant": tenant_name,
        }

        server_query = 'where it.Any("Unhandled exception:")'

        # First attempt: ±1 hour
        from_time = incident_time - datetime.timedelta(hours=1)
        to_time = incident_time + datetime.timedelta(hours=1)

        print(f"  DGrep query: XHealth / XLivesiteLog")
        print(f"  Time window: {from_time} to {to_time}")
        print(f"  Scope: Role={process_name}, Tenant={tenant_name}")
        print(f"  Server query (MQL): {server_query}")

        result = await dgrep.query(
            namespaces="XHealth",
            event_names="XLivesiteLog",
            from_time=from_time,
            to_time=to_time,
            server_query=server_query,
            server_query_type="MQL",
            scope_conditions=scope_conditions,
        )

        df = result.to_df()
        self.dgrep_link = result.get_dgrep_link()
        print(f"  DGrep link: {self.dgrep_link}")

        # Retry with wider window if no results
        if df.empty:
            print("  Results: 0 rows — widening to ±2 hours and retrying...")
            from_time_wide = incident_time - datetime.timedelta(hours=2)
            to_time_wide = incident_time + datetime.timedelta(hours=2)
            print(f"  Retry time window: {from_time_wide} to {to_time_wide}")

            result = await dgrep.query(
                namespaces="XHealth",
                event_names="XLivesiteLog",
                from_time=from_time_wide,
                to_time=to_time_wide,
                server_query=server_query,
                server_query_type="MQL",
                scope_conditions=scope_conditions,
            )
            df = result.to_df()
            self.dgrep_link = result.get_dgrep_link()
            print(f"  DGrep link (retry): {self.dgrep_link}")

        self.crash_logs = df
        self.log_count = len(df)

        if not df.empty:
            print(f"  Results: {self.log_count} rows")
            print("  Sample (first 5):")
            print(df.head(5).to_string(index=False))
        else:
            print("  Results: 0 rows — no crash logs found.")
            print("  Manual DGrep investigation may be needed.")

    # ── Step 2: Analyze error pattern ────────────────────────

    async def _step_2_analyze_error_pattern(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Classify exception from crash logs."""
        if self.log_count == 0:
            self.error_classification = "no_logs_found"
            self.error_summary = "No crash logs found in DGrep."
            print(f"  error_classification = {self.error_classification}")
            return

        df = self.crash_logs
        # Concatenate all message text for pattern scanning
        messages = []
        for _, row in df.iterrows():
            msg = str(row.get("Message", "") or row.get("message", "") or "")
            if msg.strip():
                messages.append(msg)

        combined_text = "\n".join(messages)
        print(f"  Scanning {len(messages)} log messages for patterns...")

        # ─ Check for smoke test failure ─
        is_smoke_test = False
        for keyword in _SMOKE_TEST_KEYWORDS:
            if keyword.lower() in combined_text.lower():
                is_smoke_test = True
                print(f"  Matched smoke test keyword: {keyword}")
                break

        if not is_smoke_test:
            for pattern in _AUTH_ERROR_PATTERNS:
                if pattern.lower() in combined_text.lower():
                    is_smoke_test = True
                    print(f"  Matched auth error pattern: {pattern}")
                    break

        # ─ Extract failing test name ─
        test_name_pattern = "|".join(re.escape(t) for t in _KNOWN_TEST_NAMES)
        test_match = re.search(test_name_pattern, combined_text)
        if test_match:
            self.failing_test_name = test_match.group(0)
            print(f"  failing_test_name = {self.failing_test_name}")

        # ─ Extract external service URL ─
        svc_match = re.search(r"DataSource\s*=\s*(https?://\S+)", combined_text)
        if svc_match:
            self.external_service = svc_match.group(1).rstrip(";\"'")
            print(f"  external_service = {self.external_service}")

        # ─ Extract error code ─
        code_match = re.search(
            r"(403-Forbidden|401-Unauthorized|Unauthorized|403|401|"
            r"CertificateExpiredException|KustoRequestDeniedException)",
            combined_text,
        )
        if code_match:
            self.error_code = code_match.group(0)
            print(f"  error_code = {self.error_code}")

        # ─ Extract exception type ─
        exc_match = re.search(
            r"(?:System\.)?(\w+Exception)\b", combined_text,
        )
        if exc_match:
            self.exception_type = exc_match.group(1)
            print(f"  exception_type = {self.exception_type}")

        # ─ Classify ─
        if is_smoke_test or self.failing_test_name:
            self.error_classification = "smoke_test_failure"
        elif self.exception_type in _NON_SMOKE_EXCEPTION_TYPES:
            self.error_classification = "non_smoke_test_crash"
        else:
            # Default: treat as non-smoke-test crash
            self.error_classification = "non_smoke_test_crash"

        # ─ Build error summary ─
        parts = []
        if self.exception_type:
            parts.append(self.exception_type)
        if self.failing_test_name:
            parts.append(f"in {self.failing_test_name}")
        if self.error_code:
            parts.append(f"({self.error_code})")
        if self.external_service:
            parts.append(f"calling {self.external_service}")
        self.error_summary = " ".join(parts) if parts else "Unknown exception"

        print(f"  error_classification = {self.error_classification}")
        print(f"  error_summary = {self.error_summary}")

    # ── Step 3: Check for recent deployments ─────────────────

    async def _step_3_check_deployment(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Check ADO pipelines for recent deployments in the last 3 hours."""
        process_name = tsg_input.process_name
        incident_time = tsg_input.incident_time

        # Map process name to pipeline definition ID by prefix match
        matched_service = None
        matched_def_id = None
        for prefix, (service, def_id) in _PIPELINE_MAP.items():
            if process_name.startswith(prefix):
                matched_service = service
                matched_def_id = def_id
                break

        if matched_def_id is None:
            self.pipeline_name = "Unknown"
            self.deployment_found = False
            print(f"  No pipeline mapping found for process: {process_name}")
            print("  Manual check required — inspect ADO build history.")
            # TODO: Open Question #2 — Is the process-name-to-pipeline mapping always a prefix match?
            return

        self.pipeline_name = matched_service
        self.pipeline_url = (
            f"https://msazure.visualstudio.com/One/_build?definitionId={matched_def_id}"
        )
        print(f"  Pipeline: {matched_service} (definition ID {matched_def_id})")
        print(f"  Pipeline URL: {self.pipeline_url}")

        # Query Kusto for recent builds in the last 3 hours
        from_time_str = (
            incident_time - datetime.timedelta(hours=3)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        to_time_str = incident_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        build_query = f"""
cluster('1es.kusto.windows.net').database('AzureDevOps').Build
| where EtlProcessDate between(datetime({from_time_str}) .. datetime({to_time_str}))
| where DefinitionId == {matched_def_id}
| project Result, DefinitionName, BuildId, SourceBranch,
          Timestamp=format_datetime(EtlProcessDate, 'yyyy-MM-dd HH:mm:ss')
| order by Timestamp desc
| take 10
""".strip()

        print(f"  Kusto query:\n{build_query}")

        result = await kusto.query("1es", "AzureDevOps", build_query)
        df = result.to_df()

        if not df.empty:
            print(f"  Results: {len(df)} builds found")
            print("  Sample (first 5):")
            print(df.head(5).to_string(index=False))
            self.deployment_found = True
            # Extract the most recent deployment timestamp
            if "Timestamp" in df.columns:
                self.last_deployment_time = df.iloc[0]["Timestamp"]
                print(f"  last_deployment_time = {self.last_deployment_time}")
        else:
            print("  Results: 0 builds found in last 3 hours")
            self.deployment_found = False

        print(f"  deployment_found = {self.deployment_found}")

    # ── Step 4: Route to mitigation ──────────────────────────

    async def _step_4_route_mitigation(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Route to appropriate mitigation based on classification and deployment status."""
        print(f"  error_classification = {self.error_classification}")
        print(f"  deployment_found     = {self.deployment_found}")

        if self.error_classification == "no_logs_found":
            self.mitigation_action = "pending_investigation"
            self.root_cause_summary = (
                "No crash logs found in DGrep. Manual investigation required."
            )
            self.mitigation_details = (
                "No DGrep logs found — DRI should check DGrep manually "
                f"using link: {self.dgrep_link}"
            )
            print(f"  mitigation_action = {self.mitigation_action}")
            print(f"  root_cause_summary = {self.root_cause_summary}")
            return

        # Determine mitigation path
        needs_smoke_test_mitigation = (
            self.error_classification == "smoke_test_failure"
            and self.deployment_found
        )
        needs_revert_only = (
            self.error_classification == "non_smoke_test_crash"
            and self.deployment_found
        )
        needs_escalation = not self.deployment_found

        if needs_smoke_test_mitigation:
            await self._mitigation_smoke_test(tsg_input)
        elif needs_revert_only:
            await self._mitigation_revert_deployment(tsg_input)
        elif needs_escalation:
            await self._mitigation_escalate(tsg_input)
        else:
            self.mitigation_action = "pending_investigation"
            self.root_cause_summary = self.error_summary
            self.mitigation_details = "Unhandled classification/deployment combination."
            print(f"  mitigation_action = {self.mitigation_action}")

    async def _mitigation_smoke_test(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Smoke test mitigation path: decide between revert and skip."""
        # Safety check: RunServiceBusTest must NEVER be skipped
        if self.failing_test_name in _NEVER_SKIP_TESTS:
            print(
                f"  SAFETY: {self.failing_test_name} is in NEVER_SKIP list "
                f"— routing to deployment revert only."
            )
            await self._mitigation_revert_deployment(tsg_input)
            return

        # Code bug → revert deployment
        if self.exception_type in _CODE_BUG_EXCEPTIONS:
            print(
                f"  Code bug detected ({self.exception_type}) "
                f"— routing to deployment revert."
            )
            await self._mitigation_revert_deployment(tsg_input)
            return

        # Auth/permission failure → skip smoke test
        if self.error_code or self.exception_type in (
            "KustoRequestDeniedException",
            "CertificateExpiredException",
        ):
            print(
                f"  Auth/permission failure ({self.error_code or self.exception_type}) "
                f"— routing to smoke test skip."
            )
            await self._mitigation_skip_smoke_test(tsg_input)
            return

        # Unclear → default to revert (safer)
        print("  Unclear failure type — defaulting to deployment revert (safer).")
        await self._mitigation_revert_deployment(tsg_input)

    async def _mitigation_revert_deployment(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Request human to revert the deployment."""
        self.mitigation_action = "reverted_deployment"
        self.root_cause_summary = (
            f"Process crash caused by {self.error_summary}. "
            f"Recent deployment found. Revert required."
        )
        self.mitigation_details = (
            f"Revert the most recent deployment for {self.pipeline_name} "
            f"via: {self.pipeline_url}\n"
            f"Monitor for ~15 minutes after revert for crash resolution.\n"
            f"Create a work item for root cause fix."
        )

        print("=" * 60)
        print("MANUAL ACTION REQUIRED: Revert deployment")
        print(f"  Pipeline: {self.pipeline_name}")
        print(f"  Pipeline URL: {self.pipeline_url}")
        print(f"  Last deployment: {self.last_deployment_time}")
        print(f"  Error: {self.error_summary}")
        print(f"  DGrep link: {self.dgrep_link}")
        print("  Instructions:")
        print("    1. Open the pipeline URL above")
        print("    2. Revert to the previous stable version")
        print("    3. Monitor for ~15 minutes for crash resolution")
        print("    4. Create a work item for root cause fix")
        print("=" * 60)
        # APPROVAL_GATE: Human must confirm deployment revert
        raise ManualActionRequired(
            f"Revert deployment for {self.pipeline_name} "
            f"at {self.pipeline_url}"
        )

    async def _mitigation_skip_smoke_test(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Request human to skip the failing smoke test via PR."""
        self.mitigation_action = "skipped_smoke_test"
        self.root_cause_summary = (
            f"Smoke test {self.failing_test_name} failing due to "
            f"{self.error_code or self.exception_type} "
            f"on {self.external_service or 'external service'}."
        )
        self.mitigation_details = (
            f"Submit PR to SmokeTestSettings in Storage-XInfrastructure repo "
            f'to set "{self.failing_test_name}": false.\n'
            f"Ref: https://msazure.visualstudio.com/One/_git/"
            f"Storage-XInfrastructure/commit/999f4c7f\n"
            f"Notify external service owner. Create tracking work item "
            f"to re-enable after fix."
        )

        print("=" * 60)
        print("MANUAL ACTION REQUIRED: Skip failing smoke test")
        print(f"  Failing test: {self.failing_test_name}")
        print(f"  Error: {self.error_code or self.exception_type}")
        print(f"  External service: {self.external_service or 'Unknown'}")
        print(f"  DGrep link: {self.dgrep_link}")
        print("  Instructions:")
        print("    1. Submit PR to SmokeTestSettings in Storage-XInfrastructure")
        print(f'       Set "{self.failing_test_name}": false')
        print(
            "       Ref commit: https://msazure.visualstudio.com/One/_git/"
            "Storage-XInfrastructure/commit/999f4c7f"
        )
        print("    2. Notify external service owner")
        print(
            "    3. Create tracking work item to re-enable test after "
            "external issue is resolved"
        )
        print("=" * 60)
        # APPROVAL_GATE: Human must submit the smoke test skip PR
        raise ManualActionRequired(
            f"Skip smoke test {self.failing_test_name} via PR to "
            f"Storage-XInfrastructure SmokeTestSettings"
        )

    async def _mitigation_escalate(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Escalate to service owner — no recent deployment found."""
        self.mitigation_action = "escalated_to_owner"
        self.root_cause_summary = (
            f"Process crash ({self.error_summary}) with no recent deployment. "
            f"Escalated to service owner for {tsg_input.process_name}."
        )
        self.mitigation_details = (
            f"Contacted service owner for {tsg_input.process_name}. "
            f"Provided: incident {tsg_input.incident_id}, error summary, "
            f"DGrep link, crash timeline."
        )

        print("=" * 60)
        print("MANUAL ACTION REQUIRED: Escalate to service owner")
        print(f"  Process: {tsg_input.process_name}")
        print(f"  Error: {self.error_summary}")
        print(f"  Classification: {self.error_classification}")
        print(f"  Incident ID: {tsg_input.incident_id}")
        print(f"  DGrep link: {self.dgrep_link}")
        print("  Instructions:")
        print(
            f"    1. Contact service owner for {tsg_input.process_name} "
            f"immediately (Teams/phone)"
        )
        print(
            "    2. Provide: incident ID, error summary, DGrep link, "
            "crash timeline"
        )
        print(
            "    3. If crashes ongoing and increasing → escalate to Sev-2, "
            "create bridge"
        )
        print("    4. If stabilized → keep Sev-3, monitor")
        print(
            "    5. Gather diagnostics: full stack traces, memory/CPU "
            "metrics, recent config changes, dependency health"
        )
        print("=" * 60)
        # APPROVAL_GATE: Human must contact service owner and decide severity
        raise ManualActionRequired(
            f"Escalate {tsg_input.process_name} crash to service owner. "
            f"Incident: {tsg_input.incident_id}"
        )

    # ── Step 5: Document and follow up ───────────────────────

    async def _step_5_document_followup(
        self, tsg_input: XinvestigatorProcessCrashInput,
    ) -> None:
        """Record mitigation results in ICM and create follow-up items."""
        incident_id = tsg_input.incident_id

        # Build triage summary
        summary_lines = [
            "## Automated Triage Summary (XInvestigator Process Crash TSG)",
            "",
            f"**Error Classification**: {self.error_classification}",
            f"**Exception Type**: {self.exception_type or 'N/A'}",
            f"**Error Summary**: {self.error_summary}",
            f"**Deployment Found**: {self.deployment_found}",
            f"**Mitigation Action**: {self.mitigation_action}",
            f"**Root Cause Summary**: {self.root_cause_summary}",
            "",
            f"**DGrep Link**: {self.dgrep_link}",
        ]
        if self.failing_test_name:
            summary_lines.append(
                f"**Failing Test**: {self.failing_test_name}"
            )
        if self.external_service:
            summary_lines.append(
                f"**External Service**: {self.external_service}"
            )
        if self.pipeline_url:
            summary_lines.append(
                f"**Pipeline**: {self.pipeline_name} — {self.pipeline_url}"
            )

        triage_summary = "\n".join(summary_lines)
        print(f"  Triage summary to post:\n{triage_summary}")

        # Post to ICM
        incident = await icm.get_incident(int(incident_id))
        await incident.add_description(triage_summary)
        print(f"  Posted triage summary to incident {incident_id}")

        # TODO: Open Question #1 — Create tracking work item via ADO API
        # TODO: If smoke test was skipped, create work item to re-enable test
        print(
            "  NOTE: Tracking work item creation not yet automated. "
            "DRI should create manually."
        )
        if self.mitigation_action == "skipped_smoke_test":
            print(
                f"  REMINDER: Create work item to re-enable "
                f"{self.failing_test_name} after external issue is resolved."
            )
        print(
            "  If crashes continue after mitigation, re-route to "
            "escalation path."
        )
