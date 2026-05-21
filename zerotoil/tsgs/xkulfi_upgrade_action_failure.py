"""XKulfi UpgradeActionFailure TSG.

Generated from: zero-toil/tsgs/xkulfi-upgrade-action-failure/
Source index: https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/index.md

When XKulfi's UpgradeAction retries hit ``RetryCountBeforeAlert`` (default 3),
it raises an ``UpgradeActionFailure`` ICM incident keyed by ``XKulfiAutoAlert``
and holds the rollout. This TSG:

  Step 1 — parse the incident title (tenant / operation / rollout_type /
           deployment_id / domain / target_version / app)
  Step 2 — pull recent failure logs via DGrep (alert keyword + tenant)
  Step 3 — dispatch to the per-operation ``_branch_*`` method (or generic)

Each branch produces a *triage + mitigation packet* and posts it to the
incident as a discussion entry. Mitigations themselves (DynamicSettingConfig
row insert, blob XML edit, "Skip Current Task" UI click, repo PRs) are
**always** rendered as manual instructions — never executed — because they
mutate live rollout state and require lease-owner approval per the source
TSGs. All ICM mutations (add_description / transfer / mitigate) are guarded
by ``self.dry_run``.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import ConfigDict
from xportal import dgrep, icm

from zerotoil.core.framework import (
    TsgBase,
    TsgInput,
    TsgOutput,
    dgrep_query_with_retry,
)


# ── XKulfi constants ────────────────────────────────────────

# Alert keyword used by every UpgradeActionFailure incident.
# (Source: UpgradeActionIncidentKeyword, default "XKulfiAutoAlert".)
XKULFI_ALERT_KEYWORD = "XKulfiAutoAlert"

# Storage account that hosts the per-tenant XKulfi state blobs.
XKULFI_STORAGE_ACCOUNT = "xdashxstorepublicpf"
XKULFI_BLOB_CONTAINER = "xkulfi"

# Open Question 6 (see xkulfi-upgrade-action-failure.md): the index page
# names the table ``DynamicSettingConfig`` but several per-operation TSGs
# also reference ``DynamicConfigSetting``. We default to the index spelling
# until someone confirms against the live storage account; flip this single
# constant if the actual table is the other name.
XKULFI_DYNAMIC_SETTING_TABLE = "DynamicSettingConfig"

# Escalation contacts (see _references.md).
ESCALATION_TEAM_REDMOND = ("XStore", "Deployment")
ESCALATION_CONTACT_SHANGHAI = "yazzhang"
ESCALATION_CONTACT_CHECKROLES_SHANGHAI = "liuzhouchen"


# ── Title parsing patterns (Step 1) ─────────────────────────
#
# Modern UpgradeActionFailure titles always follow the shape:
#
#   [XKulfi] [<Region>] [XStore] <Cluster> Alert: UpgradeActionFailure
#     [Tenant=<Tenant>]
#     [RepairKind=<RolloutType>]
#     [Version=<Version>]
#     [OperationName=<Operation>]
#     [ActionKey=<...>]
#
# Important: the title-prefix ``<Cluster>`` is NOT always equal to the
# ``[Tenant=...]`` value — see SampleIncidents.md ("Cluster vs Tenant name
# differ" rows). The parser must therefore prefer the ``[Tenant=...]`` token
# and never fall back to the title prefix for tenant.
#
# The ``[ActionKey=...]`` payload comes in four observed shapes (see
# SampleIncidents.md "Observations"):
#
#   A. Bracketed (per-domain):
#        [[XKulfi]<Tenant>-<RolloutType>-<DeployId>][<App>][<Version>]
#        [UpgradeDomain=N][<Timestamp>]
#   B. Bracketed (no UpgradeDomain — row 39):
#        [[XKulfi]<Tenant>-<RolloutType>-<DeployId>][<App>][<Version>][<Timestamp>]
#   C. Flat semicolon (deployment-level):
#        <Tenant>;<DeploymentId>;<App>;<Version>
#   D. Flat semicolon (CheckLeftOverMachinesBeforeUnbook):
#        <Tenant>;<App>;<DeploymentId>;<Timestamp>
#
# For OSUpgrade / FeatureFlagsUpgrade the bracketed shapes use the build
# version in the ``<DeployId>`` slot (no ``HEX:digits`` form); we keep that
# in ``deployment_id`` so the rest of the pipeline has a stable identifier.

# Source TSG capitalization is inconsistent: index page uses ``OsUpgrade``,
# real-world ICM titles use ``OSUpgrade`` (capital S). We accept both.
# ``FeatureFlagsUpgrade`` appears in production OSUpgrade variants.
_ROLLOUT_TYPES = r"ApServiceRollout|AppRollout|OSUpgrade|OsUpgrade|FeatureFlagsUpgrade"

# Standalone bracketed tokens. These are the canonical source of truth for
# tenant / operation / rollout type / version / domain — every modern title
# carries them, and the ICM ``[Tenant=...]`` value is authoritative even
# when the title-prefix cluster name disagrees.
_TENANT_TOKEN = re.compile(r"\[Tenant=(?P<tenant>[^\]]+)\]")
_OPERATION_NAME_TOKEN = re.compile(r"\[OperationName=(?P<operation>\w+)\]")
_REPAIR_KIND_TOKEN = re.compile(r"\[RepairKind=(?P<rollout_type>\w+)\]")
_VERSION_TOKEN = re.compile(r"\[Version=(?P<target_version>[^\]]+)\]")
_UPGRADE_DOMAIN_TOKEN = re.compile(r"\[UpgradeDomain=(?P<domain>\d+)\]")

# DGrep tenant — surfaced in the ICM description as a key/value pair like:
#     Icm.RaisingLocation\tXKulfiEastUS-Prod-BL2P
# In rendered ICM HTML the separator can be a tab, whitespace, a ``:``, or
# one-or-more HTML tags (``</td><td>``) between key and value. We skip any
# combination of those and capture the next identifier-like token.
_DGREP_TENANT_TOKEN = re.compile(
    r"Icm\.RaisingLocation(?:\s|[:\t]|<[^>]+>)*(?P<dgrep_tenant>[A-Za-z0-9._-]+)",
)

# Alert keyword — surfaced in the ICM description Message field as:
#     Alert keyword: <keyword> result:...
# (real example, incident 783567635:
#     Alert keyword: Upgrade action SmokeTestOperation for [[XKulfi]MS-...
#     ...[2026-04-21T10:31:42Z] result:;)
# The keyword value is bounded by the next `` result:`` token (canonical),
# or by ``;``/newline/``<`` if the description is malformed or trimmed.
# We do a non-greedy capture and stop at the first such terminator. The
# keyword body itself contains square brackets but no ``;``/``<``/newline.
_ALERT_KEYWORD_TOKEN = re.compile(
    r"Alert keyword:\s*(?P<alert_keyword>.+?)(?:\s*result:|;|[\r\n]|<)",
)

# Bracketed ActionKey payloads (shapes A and B) — applied to the inner
# payload (``[ActionKey=`` and the matching outer ``]`` already stripped).
# UpgradeDomain and target_version segments are optional; they may appear
# in either order before the trailing timestamp.
_ACTIONKEY_BRACKETED = re.compile(
    r"\[\[XKulfi\](?P<tenant>[^\]]+?)"
    r"-(?P<rollout_type>" + _ROLLOUT_TYPES + r")"
    r"-(?P<deployment_id>[^\]]+)\]"
    r"(?:\[(?P<app>[^\]]+)\])?"
    r"(?:\[(?P<target_version>[^\]]+)\])?"
    r"(?:\[UpgradeDomain=(?P<domain>\d+)\])?"
    r"(?:\[(?P<ts>[^\]]+)\])?"
)

# Flat semicolon ActionKey — Category C:
#   <Tenant>;<DeploymentId>;<App>;<Version>
# Used by deployment-level operations (ValidateBuildOperation,
# TenantHealthSignOffOperation, ScheduleXComputeJobsOperation,
# UpdateStgVersionOperation, UpdateConfigurationStorageVersionOperation,
# ResetWatchdogConfigOperation).
_ACTIONKEY_FLAT_C = re.compile(
    r"^(?P<tenant>[^;\[\]]+);"
    r"(?P<deployment_id>[0-9A-Fa-f]+:\d+);"
    r"(?P<app>APP~[^;]+);"
    r"(?P<target_version>[^\s]+)$"
)

# Flat semicolon ActionKey — Category D (CheckLeftOverMachinesBeforeUnbook):
#   <Tenant>;<App>;<DeploymentId>;<Timestamp>
_ACTIONKEY_FLAT_D = re.compile(
    r"^(?P<tenant>[^;\[\]]+);"
    r"(?P<app>APP~[^;]+);"
    r"(?P<deployment_id>[0-9A-Fa-f]+:\d+);"
    r"(?P<ts>[^\s]+)$"
)


# ── Input / Output models ───────────────────────────────────


class XKulfiUpgradeActionFailureInput(TsgInput):
    """Input for the XKulfi UpgradeActionFailure TSG."""

    model_config = ConfigDict(extra="forbid")

    time_window_hours: int = 6


class XKulfiUpgradeActionFailureOutput(TsgOutput):
    """Output for the XKulfi UpgradeActionFailure TSG."""

    model_config = ConfigDict(extra="forbid")

    tenant: str = ""
    operation: str = ""
    rollout_type: str = ""
    deployment_id: str = ""
    domain: Optional[str] = None
    target_version: Optional[str] = None
    app: Optional[str] = None
    dgrep_tenant: Optional[str] = None
    alert_keyword: Optional[str] = None
    branch_taken: str = ""
    failure_log_count: int = 0
    dgrep_link: str = ""
    mitigation_summary: str = ""


# ── TSG class ───────────────────────────────────────────────


class XKulfiUpgradeActionFailure(TsgBase):
    """Triage XKulfi UpgradeActionFailure incidents and emit a per-operation
    mitigation packet to ICM.

    Steps:
        1. Parse the ICM title to extract tenant / operation / deployment id
           / domain / target version (Step 1).
        2. Pull recent failure logs from DGrep, filtered by the
           ``XKulfiAutoAlert`` keyword (Step 2).
        3. Route to the per-operation branch and post the mitigation
           packet to ICM (Step 3 + Step 4 dispatch).
    """

    input_type = XKulfiUpgradeActionFailureInput
    output_type = XKulfiUpgradeActionFailureOutput

    # ── intermediate state (Step 1 outputs) ──
    incident_title: str = ""
    incident_create_date: Optional[datetime] = None
    tenant: str = ""
    operation: str = ""
    rollout_type: str = ""
    deployment_id: str = ""
    domain: Optional[str] = None
    target_version: Optional[str] = None
    app: Optional[str] = None
    dgrep_tenant: Optional[str] = None
    alert_keyword: Optional[str] = None

    # ── intermediate state (Step 2 outputs) ──
    failure_logs: list[dict] = []
    dgrep_link: str = ""

    # ── intermediate state (Step 4 outputs) ──
    branch_taken: str = ""
    mitigation_summary: str = ""

    # ── Routing table (operation name → method name) ─────────
    #
    # Methods are looked up by name on ``self`` in step_3 so subclasses
    # can override individual branches without touching the table.
    _ROUTES: dict[str, str] = {
        "PrepareBatchOperation":                 "_branch_prepare_batch",
        "ScheduleXComputeJobsOperation":         "_branch_schedule_xcompute",
        "UpdateStgVersionOperation":             "_branch_update_stg_version",
        "CheckRolePingAfterUnprepareOperation":  "_branch_check_role_ping_after",
        "CheckRolePingBeforeUnprepareOperation": "_branch_check_role_ping_before",
        "CheckRolesAlterationOperation":         "_branch_check_roles_alteration",
        "DeploySecretsOperation":                "_branch_deploy_secrets",
        "MonitorUpgradeBatchProgressOperation":  "_branch_monitor_upgrade_batch_progress",
        "PostPrepareBatchOperation":             "_branch_post_prepare_batch",
        "SmokeTestOperation":                    "_branch_smoke_test",
        "ValidateBuildOperation":                "_branch_validate_build",
        "ValidateRolloutEntityOperation":        "_branch_validate_rollout_entity",
    }

    # Cap recent DGrep rows attached to the evidence packet.
    _MAX_FAILURE_ROWS = 50
    _SAMPLE_LOG_COUNT = 5

    # ── Incident input extraction ────────────────────────────
    #
    # Strategy: DIRECT — the typed input only carries ``incident_id`` and
    # an optional ``time_window_hours``; structured fields are parsed in
    # Step 1 from the freshly-fetched incident.
    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> XKulfiUpgradeActionFailureInput:
        return XKulfiUpgradeActionFailureInput(incident_id=incident_id)

    # ── Top-level orchestration ──────────────────────────────

    async def _run(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> XKulfiUpgradeActionFailureOutput:
        self.failure_logs = []
        self.dgrep_link = ""
        self.branch_taken = ""
        self.mitigation_summary = ""

        await self.run_step(self.step_1_parse_incident, tsg_input)
        await self.run_step(self.step_2_fetch_failure_logs, tsg_input)
        await self.run_step(self.step_3_route_by_operation, tsg_input)

        return XKulfiUpgradeActionFailureOutput(
            tenant=self.tenant,
            operation=self.operation,
            rollout_type=self.rollout_type,
            deployment_id=self.deployment_id,
            domain=self.domain,
            target_version=self.target_version,
            app=self.app,
            dgrep_tenant=self.dgrep_tenant,
            alert_keyword=self.alert_keyword,
            branch_taken=self.branch_taken,
            failure_log_count=len(self.failure_logs),
            dgrep_link=self.dgrep_link,
            mitigation_summary=self.mitigation_summary,
        )

    # ── Step 1 — Parse incident ──────────────────────────────

    async def step_1_parse_incident(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        """Pull the incident and extract the structured XKulfi fields.

        Strategy (validated against ``SampleIncidents.md`` — 40 real titles):

        1. Pull canonical fields from the standalone bracketed tokens that
           every modern title carries:
           ``[Tenant=]``, ``[OperationName=]``, ``[RepairKind=]``,
           ``[Version=]``, ``[UpgradeDomain=]``.
           The ``[Tenant=...]`` token is **authoritative** — the title prefix
           often shows a different cluster name (e.g. row 19's prefix is
           ``MS-BLZ04PrdStez100A`` but tenant is ``MS-MNZ09PrdSte100A``).
        2. Locate the ``[ActionKey=...]`` payload (using bracket-depth
           matching to handle the nested square brackets cleanly), then
           parse it against one of the four observed shapes (bracketed
           with/without UpgradeDomain, flat C, flat D) to recover
           ``deployment_id`` / ``app`` and to fill any token gaps.
        3. If the title is missing tokens (e.g. trimmed/truncated), retry
           the same extraction against each ICM description body.

        Coding ability: icm-get-incident
        AUTOMATABLE: Yes.
        """
        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=True,
        )
        title = incident.Title or ""
        self.incident_title = title
        self.incident_create_date = incident.CreateDate
        print(f"  Incident {tsg_input.incident_id} title: {title!r}")
        print(f"  CreateDate: {self.incident_create_date}")

        # Reset Step 1 state so reruns don't carry stale values.
        self.tenant = ""
        self.operation = ""
        self.rollout_type = ""
        self.deployment_id = ""
        self.domain = None
        self.target_version = None
        self.app = None
        self.dgrep_tenant = None
        self.alert_keyword = None

        description_texts: list[str] = []
        for desc in (getattr(incident, "Descriptions", None) or []):
            text = getattr(desc, "Text", None)
            if text:
                description_texts.append(text)

        # Pass 1 — bracketed tokens (title first, descriptions to fill gaps).
        title_token_hits = self._extract_from_tokens(title)
        for text in description_texts:
            if self.tenant and self.operation and self.rollout_type \
                    and self.target_version and self.domain is not None:
                break
            self._extract_from_tokens(text, fill_missing_only=True)
        if title_token_hits:
            print(f"  Tokens parsed from title: {sorted(title_token_hits)}")

        # Pass 2 — ActionKey payload (title first, descriptions as fallback).
        action_key_payload = self._extract_action_key_payload(title)
        if action_key_payload is None:
            for text in description_texts:
                action_key_payload = self._extract_action_key_payload(text)
                if action_key_payload is not None:
                    print("  ActionKey payload found in description.")
                    break
        if action_key_payload is not None:
            shape = self._parse_action_key_payload(action_key_payload)
            print(f"  ActionKey shape: {shape}")
        else:
            print("  WARNING: No [ActionKey=...] payload found in title or description.")

        if not self.operation:
            print(
                "  WARNING: Could not parse OperationName from title or "
                "description; Step 3 will route to the generic branch."
            )

        # Pass 3 — dgrep_tenant from the description ``Icm.RaisingLocation``
        # key/value pair (per step-1-parse-incident.md). The DGrep tenant is
        # distinct from the rollout tenant (e.g. tenant=MS-IAD04PrdStp02A,
        # dgrep_tenant=XKulfiEastUS-Prod-BL2P) and is required by Step 2.
        for text in description_texts:
            m = _DGREP_TENANT_TOKEN.search(text)
            if m:
                self.dgrep_tenant = m.group("dgrep_tenant").strip()
                print(f"  dgrep_tenant resolved from description: {self.dgrep_tenant}")
                break
        if self.dgrep_tenant is None:
            print(
                "  WARNING: No 'Icm.RaisingLocation' key/value found in "
                "description; Step 2 will fall back to the rollout tenant for "
                "the DGrep scope."
            )

        # Pass 4 — alert_keyword from the description ``Alert keyword: <kw>``
        # key/value pair (per step-1-parse-incident.md). The keyword is the
        # exact ``XKulfiAutoAlert`` payload that fired the incident and
        # narrows the DGrep search to the offending action instance.
        for text in description_texts:
            m = _ALERT_KEYWORD_TOKEN.search(text)
            if m:
                self.alert_keyword = m.group("alert_keyword").strip()
                print(f"  alert_keyword resolved from description: {self.alert_keyword}")
                break
        if self.alert_keyword is None:
            print(
                "  WARNING: No 'Alert keyword:' value found in description; "
                "Step 2 will fall back to the generic XKulfiAutoAlert keyword."
            )

        print(f"  operation       = {self.operation!r}")
        print(f"  tenant          = {self.tenant!r}")
        print(f"  rollout_type    = {self.rollout_type!r}")
        print(f"  deployment_id   = {self.deployment_id!r}")
        print(f"  domain          = {self.domain!r}")
        print(f"  target_version  = {self.target_version!r}")
        print(f"  app             = {self.app!r}")
        print(f"  dgrep_tenant    = {self.dgrep_tenant!r}")
        print(f"  alert_keyword   = {self.alert_keyword!r}")

    # ── Step 1 helpers ───────────────────────────────────────

    def _extract_from_tokens(
        self, text: str, *, fill_missing_only: bool = False,
    ) -> set[str]:
        """Extract canonical fields from standalone bracketed tokens.

        Returns the set of field names that were populated by this call.
        When ``fill_missing_only`` is True, only currently-empty fields are
        overwritten (used for description fallback so the title remains
        the source of truth).
        """
        hits: set[str] = set()

        def _set(field: str, value: Optional[str]) -> None:
            if not value:
                return
            current = getattr(self, field)
            if fill_missing_only and current:
                return
            setattr(self, field, value.strip())
            hits.add(field)

        m = _TENANT_TOKEN.search(text)
        if m:
            _set("tenant", m.group("tenant"))
        m = _OPERATION_NAME_TOKEN.search(text)
        if m:
            _set("operation", m.group("operation"))
        m = _REPAIR_KIND_TOKEN.search(text)
        if m:
            _set("rollout_type", m.group("rollout_type"))
        m = _VERSION_TOKEN.search(text)
        if m:
            _set("target_version", m.group("target_version"))
        m = _UPGRADE_DOMAIN_TOKEN.search(text)
        if m:
            _set("domain", m.group("domain"))

        return hits

    @staticmethod
    def _extract_action_key_payload(text: str) -> Optional[str]:
        """Return the substring inside ``[ActionKey=...]``.

        Uses bracket-depth matching (not a single regex) because the payload
        itself contains square brackets in shapes A and B. Returns ``None``
        if no ``[ActionKey=`` token is present or the brackets are
        unbalanced (e.g. a truncated title — see SampleIncidents.md row 37).
        """
        marker = "[ActionKey="
        start = text.find(marker)
        if start < 0:
            return None
        i = start + len(marker)
        depth = 1
        j = i
        while j < len(text):
            ch = text[j]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[i:j]
            j += 1
        return None  # unbalanced — caller logs a warning

    def _parse_action_key_payload(self, payload: str) -> str:
        """Parse an extracted ActionKey payload and fill any missing fields.

        Returns a short shape label for logging.
        """
        # Shape A/B — bracketed (per-domain or no-UpgradeDomain).
        m = _ACTIONKEY_BRACKETED.match(payload)
        if m:
            g = m.groupdict()
            self._fill_missing("tenant", g.get("tenant"))
            self._fill_missing("rollout_type", g.get("rollout_type"))
            # ``deployment_id`` is only available from ActionKey; always set.
            if g.get("deployment_id"):
                self.deployment_id = g["deployment_id"].strip()
            self._fill_missing("app", g.get("app"))
            self._fill_missing("target_version", g.get("target_version"))
            self._fill_missing("domain", g.get("domain"))
            return "bracketed-with-domain" if g.get("domain") else "bracketed"
        # Shape C — flat semicolon (deployment-level).
        m = _ACTIONKEY_FLAT_C.match(payload)
        if m:
            g = m.groupdict()
            self._fill_missing("tenant", g.get("tenant"))
            if g.get("deployment_id"):
                self.deployment_id = g["deployment_id"].strip()
            self._fill_missing("app", g.get("app"))
            self._fill_missing("target_version", g.get("target_version"))
            return "flat-tenant;dep;app;ver"
        # Shape D — flat semicolon (CheckLeftOverMachinesBeforeUnbook).
        m = _ACTIONKEY_FLAT_D.match(payload)
        if m:
            g = m.groupdict()
            self._fill_missing("tenant", g.get("tenant"))
            if g.get("deployment_id"):
                self.deployment_id = g["deployment_id"].strip()
            self._fill_missing("app", g.get("app"))
            return "flat-tenant;app;dep;ts"
        print(f"  WARNING: Unrecognized ActionKey payload shape: {payload!r}")
        return "unknown"

    def _fill_missing(self, field: str, value: Optional[str]) -> None:
        """Set ``field`` to ``value`` only if currently empty."""
        if not value:
            return
        if not getattr(self, field):
            setattr(self, field, value.strip())

    # ── Step 2 — Fetch failure logs ──────────────────────────

    async def step_2_fetch_failure_logs(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        """Pull recent XKulfi action-result log rows for this incident.

        Per ``step-2-fetch-failure-logs.md``, the canonical DGrep query is:

            Namespace:  XKulfiTelemetry
            EventName:  TraceTelemetry
            Tenant:     <dgrep_tenant>           (e.g. XKulfiEastUS-Prod-BL2P)
            Role:       XKulfi
            Server Query:
                where message.contains("<alert_keyword> result:")
                select STG_TenantName, STG_VirtualTenantName,
                       STG_PFEnvironment, message, PreciseTimeStamp,
                       RoleInstance, Tenant

        Both ``dgrep_tenant`` and ``alert_keyword`` come from Step 1
        (description scrape). If either is missing the query is skipped
        and Step 3 still runs with whatever evidence we have.

        Coding ability: dgrep-query
        AUTOMATABLE: Yes (DGrep portion). Blob XML history is left as a
        path string for human inspection (Open Question 2-2).
        """
        anchor = self.incident_create_date or datetime.now(timezone.utc)
        from_time = anchor - timedelta(hours=tsg_input.time_window_hours)
        to_time = anchor + timedelta(minutes=30)

        # The new query targets XKulfiTelemetry/TraceTelemetry scoped to
        # the XKulfi role on the dgrep_tenant resolved from the description
        # (e.g. ``XKulfiEastUS-Prod-BL2P``). The dgrep_tenant is distinct
        # from the rollout tenant and is required by this namespace —
        # falling back to ``self.tenant`` here would query the wrong scope.
        if not self.dgrep_tenant:
            print(
                "  Skipping DGrep query — no dgrep_tenant parsed from "
                "incident description (Icm.RaisingLocation key/value); "
                "Step 3 will still run with title-only evidence."
            )
            return
        if not self.alert_keyword:
            print(
                "  Skipping DGrep query — no alert_keyword parsed from "
                "incident description; the message.contains(...) filter "
                "would match every TraceTelemetry row for the tenant."
            )
            return

        scope = {"Tenant": self.dgrep_tenant, "Role": "XKulfi"}
        # Escape any double-quotes inside the keyword so the MQL string
        # literal stays valid; the real keyword bodies seen in production
        # contain ``[``/``]``/``=``/``:`` but no quotes.
        keyword_literal = self.alert_keyword.replace('"', '\\"')
        server_query = (
            f'where message.contains("{keyword_literal}") '
            "select STG_TenantName, STG_VirtualTenantName, STG_PFEnvironment, "
            "message, PreciseTimeStamp, RoleInstance, Tenant"
        )

        print(f"  Namespace=XKulfiTelemetry EventName=TraceTelemetry")
        print(f"  Scope: Tenant={self.dgrep_tenant} Role=XKulfi")
        print(f"  From: {from_time.isoformat()}  To: {to_time.isoformat()}")

        # Build the shareable DGrep portal URL up-front (no query call) so
        # operators can open it even when the managed identity lacks data
        # permission for ``XKulfiTelemetry`` and the query below fails.
        try:
            self.dgrep_link = dgrep.get_dgrep_link(
                namespaces="XKulfiTelemetry",
                event_names="TraceTelemetry",
                from_time=from_time,
                to_time=to_time,
                server_query=server_query,
                server_query_type="MQL",
                scope_conditions=scope,
                environment="Production",
            ) or ""
        except Exception as exc:
            print(f"  WARNING: Could not build DGrep link: {exc}")
            self.dgrep_link = ""
        if self.dgrep_link:
            print(f"  DGrep link: {self.dgrep_link}")

        try:
            result = await dgrep_query_with_retry(
                dgrep,
                namespaces="XKulfiTelemetry",
                event_names="TraceTelemetry",
                from_time=from_time,
                to_time=to_time,
                server_query=server_query,
                server_query_type="MQL",
                scope_conditions=scope,
                environment="Production",
            )
        except Exception as exc:
            print(f"  WARNING: DGrep query failed after retries: {exc}")
            print("  Continuing without DGrep rows; branch + ICM evidence still run.")
            return

        df = result.to_df()
        # Prefer the post-query link if available (it preserves the exact
        # parameters the service actually used); otherwise keep the
        # pre-built link from above.
        try:
            post_link = result.get_dgrep_link() or ""
            if post_link:
                self.dgrep_link = post_link
        except Exception:
            pass
        print(f"  Results: {len(df)} rows")

        if df is None or df.empty:
            print(
                "  No XKulfi action-result rows in window; Step 4z will "
                "still run with title-only evidence."
            )
            return

        df.columns = df.columns.str.lower()
        # Sort newest-first then cap.
        if "precisetimestamp" in df.columns:
            df = df.sort_values("precisetimestamp", ascending=False)
        df = df.head(self._MAX_FAILURE_ROWS)

        print(f"  Sample (first {self._SAMPLE_LOG_COUNT}):")
        print(df.head(self._SAMPLE_LOG_COUNT).to_string(index=False))

        rows: list[dict] = []
        for _, row in df.iterrows():
            msg = str(row.get("message", ""))
            ts = str(row.get("precisetimestamp", ""))
            exc_type = self._extract_exception_type(msg)
            rows.append(
                {
                    "ts": ts,
                    "exception_type": exc_type,
                    "message": msg,
                    "role_instance": str(row.get("roleinstance", "")),
                    "stg_tenant": str(row.get("stg_tenantname", "")),
                    "stg_virtual_tenant": str(row.get("stg_virtualtenantname", "")),
                    "stg_pf_environment": str(row.get("stg_pfenvironment", "")),
                }
            )
        self.failure_logs = rows
        print(f"  Captured {len(self.failure_logs)} failure rows for the evidence packet.")

    @staticmethod
    def _extract_exception_type(msg: str) -> str:
        """Best-effort exception-type extraction from a log message."""
        m = re.search(r"([A-Za-z][\w\.]*Exception)\b", msg)
        return m.group(1) if m else ""

    # ── Step 3 — Route by operation ──────────────────────────

    async def step_3_route_by_operation(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        """Dispatch to the per-operation ``_branch_*`` method.

        Coding ability: none (pure dict lookup).
        AUTOMATABLE: Yes.
        """
        method_name = self._ROUTES.get(self.operation, "_branch_generic")
        self.branch_taken = method_name
        print(f"  operation={self.operation!r} → {method_name}")

        branch_method = getattr(self, method_name)
        await branch_method(tsg_input)

    # ── Branch helpers ───────────────────────────────────────

    def _print_banner(self, branch_label: str) -> None:
        print("=" * 70)
        print(f"BRANCH: {branch_label}")
        print(f"  tenant         = {self.tenant or '<unknown>'}")
        print(f"  operation      = {self.operation or '<unknown>'}")
        print(f"  rollout_type   = {self.rollout_type or '<unknown>'}")
        print(f"  deployment_id  = {self.deployment_id or '<unknown>'}")
        print(f"  domain         = {self.domain or '<n/a>'}")
        print(f"  target_version = {self.target_version or '<n/a>'}")
        print("=" * 70)

    def _format_skip_config_row(
        self,
        config_field: str = "RetryCountBeforeSkip",
        value: str = "10",
        include_domain: bool = False,
    ) -> str:
        """Render the exact DynamicSettingConfig row an operator would insert.

        ``include_domain=True`` adds the per-domain RowKey suffix (used by
        domain-level operations like CheckRolePing*, MonitorUpgradeBatch,
        SmokeTest, CheckRolesAlteration).
        """
        rollout = self.rollout_type or "<RolloutType>"
        row_key = f"{self.operation}.{config_field} | {rollout}"
        if include_domain:
            row_key += f" | {self.domain or '<Domain>'}"

        # ValidBefore = now + 24h ISO8601 (so the override expires automatically).
        valid_before = (
            datetime.now(timezone.utc) + timedelta(hours=24)
        ).isoformat()

        lines = [
            f"  Table:        {XKULFI_DYNAMIC_SETTING_TABLE}",
            f"  Account:      {XKULFI_STORAGE_ACCOUNT}",
            f"  PartitionKey: {self.tenant or '<Tenant>'}",
            f"  RowKey:       {row_key}",
            f"  DeploymentId: {self.deployment_id or '<DeploymentId>'}",
            f"  Value:        {value}",
            f"  UpdatedBy:    <your-alias>",
            f"  ValidBefore:  {valid_before}",
        ]
        return "\n".join(lines)

    def _build_evidence_summary(
        self,
        branch_label: str,
        diagnosis: str,
        manual_actions: list[str],
        skip_row: Optional[str] = None,
        extra_links: Optional[list[str]] = None,
    ) -> str:
        """Render the Markdown evidence body posted to ICM."""
        parts = [
            f"## XKulfi UpgradeActionFailure triage — {branch_label}",
            "",
            f"- Tenant:         `{self.tenant or '<unknown>'}`",
            f"- Operation:      `{self.operation or '<unknown>'}`",
            f"- RolloutType:    `{self.rollout_type or '<unknown>'}`",
            f"- DeploymentId:   `{self.deployment_id or '<unknown>'}`",
            f"- Domain:         `{self.domain or '<n/a>'}`",
            f"- TargetVersion:  `{self.target_version or '<n/a>'}`",
            f"- App:            `{self.app or '<n/a>'}`",
            "",
            "### Diagnosis",
            diagnosis or "_(none)_",
            "",
            "### Manual mitigation steps",
        ]
        if manual_actions:
            for i, action in enumerate(manual_actions, start=1):
                parts.append(f"{i}. {action}")
        else:
            parts.append("_(none — escalation only)_")

        if skip_row:
            parts.append("")
            parts.append("### Suggested DynamicSettingConfig skip row (manual insert only)")
            parts.append("```")
            parts.append(skip_row)
            parts.append("```")

        parts.append("")
        parts.append("### Evidence")
        parts.append(f"- Failure log rows captured: {len(self.failure_logs)}")
        if self.dgrep_link:
            parts.append(f"- DGrep query: {self.dgrep_link}")
        if self.tenant and self.operation:
            blob_path = (
                f"{XKULFI_STORAGE_ACCOUNT}/{XKULFI_BLOB_CONTAINER}/"
                f"TenantStatus/{self.tenant}/{self.operation}"
            )
            parts.append(f"- History XML (manual read): `{blob_path}`")
        for link in extra_links or []:
            parts.append(f"- {link}")

        # Include up to 5 most-recent failure rows verbatim (truncated).
        if self.failure_logs:
            parts.append("")
            parts.append("### Recent failure rows (most recent first)")
            for row in self.failure_logs[: self._SAMPLE_LOG_COUNT]:
                msg = (row.get("message") or "").replace("\n", " ")
                if len(msg) > 400:
                    msg = msg[:400] + "..."
                ts = row.get("ts", "")
                exc = row.get("exception_type") or "?"
                parts.append(f"- `{ts}` [{exc}] {msg}")

        return "\n".join(parts)

    async def _post_evidence(
        self, tsg_input: XKulfiUpgradeActionFailureInput, summary: str,
    ) -> None:
        """Post the mitigation packet to ICM as a description entry.

        Always guarded by ``self.dry_run``.
        """
        self.mitigation_summary = summary

        if self.dry_run:
            print(f"  [DRY-RUN] Would post evidence to ICM {tsg_input.incident_id}")
            print(f"  [DRY-RUN] Evidence summary:\n{summary}")
            return

        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False,
        )
        await incident.add_description(summary)
        print(f"  Evidence posted to ICM {tsg_input.incident_id}")

    def _parse_unresponsive_machines(self) -> list[str]:
        """Best-effort extraction of role-instance / machine names from logs."""
        names: list[str] = []
        seen: set[str] = set()
        # Common XStore role-instance / machine name prefixes.
        pattern = re.compile(r"\b([A-Z]{2,}[A-Z0-9]{2,}[A-Z0-9_]{2,})\b")
        for row in self.failure_logs:
            for m in pattern.finditer(row.get("message", "")):
                token = m.group(1)
                if token in seen:
                    continue
                # Filter out obvious noise tokens.
                if token in {"INFO", "WARN", "ERROR", "DEBUG", "TRACE", "FATAL", "MQL", "UTC"}:
                    continue
                seen.add(token)
                names.append(token)
        return names[:50]

    # ── Branch: PrepareBatchOperation (step-4a) ──────────────

    async def _branch_prepare_batch(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("PrepareBatchOperation (step-4a)")
        # Open Question 4a-1: xds-api-call UpgradeStateApi may expose the
        # in-flight prep task name; until verified we surface the manual
        # path and let the operator screenshot Troubleshooting info.
        manual = [
            "Open the incident in ICM and copy the XDS 'current task' name "
            "from Troubleshooting Info (e.g., `CheckQuorumTask::XvExtentManagerRole`).",
            "Treat as a Fabric XDS preparation issue — reuse the Fabric "
            "deployment knowledge for the named task.",
            "**Preprod only, with lease-owner approval**: XDS UI ▸ Tenant Status "
            "▸ Upgrade State ▸ Advanced Operations ▸ 'Skip Current Task'. "
            "Do NOT click in Prod.",
            "If you cannot identify the task or skip is not approved, escalate "
            f"to {ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]} "
            f"(Redmond) or {ESCALATION_CONTACT_SHANGHAI} (Shanghai).",
        ]
        skip_row = self._format_skip_config_row(include_domain=True)

        print("Manual action required: identify XDS current task and consider 'Skip Current Task' (Preprod only).")
        print(skip_row)

        summary = self._build_evidence_summary(
            "PrepareBatchOperation",
            "XDS domain preparation timed out; suspected stuck XDS task on the active UD.",
            manual,
            skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: ScheduleXComputeJobsOperation (step-4b) ──────

    async def _branch_schedule_xcompute(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("ScheduleXComputeJobsOperation (step-4b)")
        # Open Question 4b-1: no DC-version API surfaced via current
        # coding abilities — we leave the DC parity check as manual.
        manual = [
            "Probe tenant reachability in XDS UI / XCompute tab "
            f"(`{self.tenant}`).",
            "Compare the tenant's DC version against the rollout's target "
            "STG build; if DC is outdated, update DC and wait for the next "
            "XKulfi auto-retry (auto-mitigates on success).",
            "Oncall path (lease-owner approval): insert the skip row below "
            f"into `{XKULFI_DYNAMIC_SETTING_TABLE}` to bypass the action; "
            "do NOT write programmatically.",
            f"If still stuck after skip, escalate to "
            f"{ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]} "
            f"(Redmond) or {ESCALATION_CONTACT_SHANGHAI} (Shanghai).",
        ]
        skip_row = self._format_skip_config_row()
        print(skip_row)
        summary = self._build_evidence_summary(
            "ScheduleXComputeJobsOperation",
            "Failed to schedule eligible XCompute jobs after rollout.",
            manual,
            skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: UpdateStgVersionOperation (step-4c) ──────────

    async def _branch_update_stg_version(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("UpdateStgVersionOperation (step-4c)")
        manual = [
            "Probe tenant reachability in XDS UI; verify EnPns and recent "
            "smoke results.",
            "Check tenant DC version vs target STG build; update DC if "
            "outdated and wait for the next auto-retry.",
            "Oncall path (lease-owner approval): insert the skip row below "
            f"into `{XKULFI_DYNAMIC_SETTING_TABLE}`; do NOT write programmatically.",
            f"If still stuck, escalate to "
            f"{ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]} "
            f"or {ESCALATION_CONTACT_SHANGHAI}.",
        ]
        skip_row = self._format_skip_config_row()
        print(skip_row)
        signature = ""
        for row in self.failure_logs:
            if row.get("exception_type"):
                signature = row["exception_type"]
                break
        diagnosis = (
            "Failed to update STG versions in metadata after rollout."
            + (f" Detected exception: `{signature}`." if signature else "")
        )
        summary = self._build_evidence_summary(
            "UpdateStgVersionOperation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: CheckRolePingAfterUnprepareOperation (step-4d) ─

    async def _branch_check_role_ping_after(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        await self._branch_check_role_ping_common(
            tsg_input,
            label="CheckRolePingAfterUnprepareOperation (step-4d)",
            phase="after",
        )

    # ── Branch: CheckRolePingBeforeUnprepareOperation (step-4e) ─

    async def _branch_check_role_ping_before(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        await self._branch_check_role_ping_common(
            tsg_input,
            label="CheckRolePingBeforeUnprepareOperation (step-4e)",
            phase="before",
        )

    async def _branch_check_role_ping_common(
        self,
        tsg_input: XKulfiUpgradeActionFailureInput,
        *,
        label: str,
        phase: str,
    ) -> None:
        self._print_banner(label)
        candidate_roles = self._parse_unresponsive_machines()
        if candidate_roles:
            print(f"  Candidate unresponsive role-instance tokens (top 20):")
            for name in candidate_roles[:20]:
                print(f"    - {name}")
        else:
            print("  No role-instance candidates parsed from logs.")

        # Open Question 4d-1: programmatic role-list extraction is best-effort
        # against DGrep messages; the canonical list is in the ICM
        # Troubleshooting Info HTML body.
        manual = [
            f"XKulfi reports too many role instances unresponsive **{phase}** "
            "unpreparing the UD; copy the canonical unresponsive list from "
            "the incident's Troubleshooting Info.",
            "Confirm via XDS UI (RoleInstancesApi role ping) for each name.",
            "**Preprod only**: restart the unresponsive role instances first; "
            "investigate logs if still unresponsive.",
            "If machines are unhealthy, DM auto-initiates repair — wait and "
            "monitor; do not manually restart.",
            "Oncall (lease-owner approval): insert the per-domain skip row "
            f"below into `{XKULFI_DYNAMIC_SETTING_TABLE}`; do NOT write "
            "programmatically.",
            f"Otherwise escalate to "
            f"{ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]} "
            f"(Redmond) or {ESCALATION_CONTACT_SHANGHAI} (Shanghai).",
        ]
        skip_row = self._format_skip_config_row(include_domain=True)
        print(skip_row)
        diagnosis = (
            f"Role instances reported unresponsive {phase} unprepare on "
            f"domain `{self.domain or '<unknown>'}`."
        )
        if candidate_roles:
            diagnosis += (
                "\n\nBest-effort role-instance tokens parsed from logs: "
                + ", ".join(f"`{r}`" for r in candidate_roles[:20])
            )
        summary = self._build_evidence_summary(label, diagnosis, manual, skip_row)
        await self._post_evidence(tsg_input, summary)

    # ── Branch: CheckRolesAlterationOperation (step-4f) ──────

    async def _branch_check_roles_alteration(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("CheckRolesAlterationOperation (step-4f)")
        # Open Question 4f-1: no API to look up "who triggered this deployment".
        manual = [
            "Default response: locate the engineer who triggered this "
            "deployment and ask them to **cancel** it.",
            f"If unreachable during Shanghai hours, escalate to "
            f"{ESCALATION_CONTACT_CHECKROLES_SHANGHAI} (XKulfi Shanghai for "
            "CheckRolesAlteration).",
            "If the role alteration is intentional and approved by the lease "
            f"owner, insert the appropriate Allow* row into "
            f"`{XKULFI_DYNAMIC_SETTING_TABLE}` (RowKey one of: "
            "`CheckRolesAlterationOperation.AllowRemoveInstanceOfRoles`, "
            "`AllowAddInstanceOfRoles`, or `AllowRemoveRoles`); see the "
            "skip-row template below for the column layout. Value should be "
            "the affected role name wrapped in `<string>...</string>`. "
            "Do NOT auto-cancel and do NOT write the row programmatically.",
        ]
        # Render with the Allow* placeholder so operator can swap the kind.
        skip_row = self._format_skip_config_row(
            config_field="AllowRemoveInstanceOfRoles | <or AllowAddInstanceOfRoles | AllowRemoveRoles>",
            value="<string>AffectedRoleName</string>",
            include_domain=True,
        )
        print(skip_row)
        diagnosis = (
            "Roles were added/removed/instance-count-changed in the new STG "
            "build; XKulfi blocked the rollout before unpreparing the first UD."
        )
        summary = self._build_evidence_summary(
            "CheckRolesAlterationOperation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: DeploySecretsOperation (step-4g) ─────────────

    async def _branch_deploy_secrets(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("DeploySecretsOperation (step-4g)")
        signature = ""
        for row in self.failure_logs:
            if "SecretsConfigLibException" in row.get("message", ""):
                signature = "SecretsConfigLibException"
                break
            if row.get("exception_type") and not signature:
                signature = row["exception_type"]

        manual = [
            "Collect the SecretsConfigLib logs from the failed XKulfi job "
            "(per Step 2 DGrep link).",
            "If the failure is recurring, file a bug item against the "
            "secrets pipeline owners.",
            "If no new secret was added in the target STG build (~99% of "
            "cases), insert the skip row below into "
            f"`{XKULFI_DYNAMIC_SETTING_TABLE}`; do NOT write programmatically.",
            f"Otherwise escalate to "
            f"{ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]} "
            f"or {ESCALATION_CONTACT_SHANGHAI}.",
        ]
        skip_row = self._format_skip_config_row()
        print(skip_row)
        diagnosis = (
            "Failed to deploy secrets for the target STG build."
            + (f" Detected signature: `{signature}`." if signature else "")
        )
        summary = self._build_evidence_summary(
            "DeploySecretsOperation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: MonitorUpgradeBatchProgressOperation (step-4h) ─

    async def _branch_monitor_upgrade_batch_progress(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("MonitorUpgradeBatchProgressOperation (step-4h)")
        candidate_machines = self._parse_unresponsive_machines()
        if candidate_machines:
            print(f"  Candidate unhealthy machine tokens (top 20):")
            for name in candidate_machines[:20]:
                print(f"    - {name}")

        # Open Question 4h-1/2/3: no coding ability for XTS watchdog,
        # smoke history, or 'Trigger manual repair' Geneva Action.
        manual = [
            "For each unhealthy machine, check XTS watchdog errors (Fabric XTS).",
            "If an XStore role is unresponsive on a healthy machine, suggest "
            "a manual restart of that role (Preprod only, lease-owner approval).",
            "If hardware/machine error, escalate to **XSSE**.",
            "Check smoke test history in XDS UI; if smoke is failing, follow "
            "the Fabric **Master TSG**: "
            "https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/"
            "azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/"
            "stgos/incidents/_master_tsg",
            "Oncall path: trigger manual repair via the Geneva Action linked "
            "from https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/"
            "azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/"
            "xpfdeployment/xkulfi/operation_document/triggermanualrepair, "
            "or escalate to XSSE for node recovery.",
            "If lease owner approves a skip, insert the per-domain row below "
            f"into `{XKULFI_DYNAMIC_SETTING_TABLE}`; do NOT write programmatically.",
        ]
        skip_row = self._format_skip_config_row(include_domain=True)
        print(skip_row)
        diagnosis = (
            f"Active upgrade batch (domain `{self.domain or '<unknown>'}`) "
            "has unhealthy machines; XKulfi is holding the rollout."
        )
        if candidate_machines:
            diagnosis += (
                "\n\nBest-effort machine tokens parsed from logs: "
                + ", ".join(f"`{m}`" for m in candidate_machines[:20])
            )
        summary = self._build_evidence_summary(
            "MonitorUpgradeBatchProgressOperation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: PostPrepareBatchOperation (step-4i) ──────────

    async def _branch_post_prepare_batch(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("PostPrepareBatchOperation (step-4i)")
        # Detect the documented KeyNotFoundException + release/26.0122.1.0 pattern.
        is_known_keyerror = False
        for row in self.failure_logs:
            msg = row.get("message", "")
            if "KeyNotFoundException" in msg and "release/26.0122.1.0" in msg:
                is_known_keyerror = True
                break

        # Open Question 4i-2: cannot determine XUTLT presence without reading
        # the blob — surface the conditional in the manual instructions.
        tenant_for_blob = self.tenant or "<virtual-tenant>"
        blob_path = (
            f"{XKULFI_STORAGE_ACCOUNT}/{XKULFI_BLOB_CONTAINER}/"
            f"TenantStatus/{tenant_for_blob}/TenantRolloutInfo"
        )
        xml_template = (
            '<UpgradedMachineFunctionMachinesMappings xmlns:d2p1='
            '"http://schemas.microsoft.com/2003/10/Serialization/Arrays">\n'
            '    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '        <d2p1:Key>XRSL</d2p1:Key>\n'
            '        <d2p1:Value></d2p1:Value>\n'
            '    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '        <d2p1:Key>XUTLT</d2p1:Key>\n'
            '        <d2p1:Value></d2p1:Value>\n'
            '    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '        <d2p1:Key>XBE</d2p1:Key>\n'
            '        <d2p1:Value></d2p1:Value>\n'
            '    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '        <d2p1:Key>XMGMT</d2p1:Key>\n'
            '        <d2p1:Value></d2p1:Value>\n'
            '    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>\n'
            '</UpgradedMachineFunctionMachinesMappings>'
        )

        if is_known_keyerror:
            diagnosis = (
                "**Known signature matched**: `KeyNotFoundException` with app "
                "version `release/26.0122.1.0`. Mitigated by injecting "
                "`UpgradedMachineFunctionMachinesMappings` into the "
                "TenantRolloutInfo blob."
            )
            manual = [
                f"Open the blob `{blob_path}` in Azure Storage Explorer "
                "(or equivalent) — read-only first.",
                "Append the XML block below directly under the `<UpdatedTime>` "
                "element. **Remove the `XUTLT` block** if this tenant does "
                "not have an `XUTLT` machine function (verify in XDS).",
                "Bump the `<DateTime>` value inside `<UpdatedTime>` to a "
                "future UTC timestamp so XKulfi reloads the file.",
                "Upload-to-replace the blob. **Do NOT script this** — every "
                "byte must be reviewed by the lease owner.",
                "After the next auto-retry succeeds XKulfi auto-mitigates "
                "the incident.",
                "XML insertion template:\n```xml\n" + xml_template + "\n```",
            ]
        else:
            diagnosis = (
                "PostPrepareBatchOperation failed but the failure does NOT "
                "match the known `KeyNotFoundException` + `release/26.0122.1.0` "
                "pattern. Treating as generic — escalating."
            )
            manual = [
                "Inspect the failure_logs section below for the exception type.",
                f"Read the TenantRolloutInfo blob manually for context: "
                f"`{blob_path}`.",
                f"Escalate to {ESCALATION_TEAM_REDMOND[0]}/"
                f"{ESCALATION_TEAM_REDMOND[1]} (Redmond) or "
                f"{ESCALATION_CONTACT_SHANGHAI} (Shanghai).",
            ]

        # No skip-row for this branch — mitigation is the XML edit.
        print(f"Manual blob to edit: {blob_path}")
        print(f"Known KeyError pattern matched: {is_known_keyerror}")
        summary = self._build_evidence_summary(
            "PostPrepareBatchOperation", diagnosis, manual,
            extra_links=[f"TenantRolloutInfo blob: `{blob_path}`"],
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: SmokeTestOperation (step-4j) ─────────────────

    async def _branch_smoke_test(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("SmokeTestOperation (step-4j)")
        # Best-effort failing-case extraction (looks for HealthChecks/Suite paths).
        failing: list[str] = []
        seen: set[str] = set()
        case_pattern = re.compile(r"([A-Za-z][\w\-]*Suite/[^\s,;]+)")
        for row in self.failure_logs:
            for m in case_pattern.finditer(row.get("message", "")):
                name = m.group(1)
                if name not in seen:
                    seen.add(name)
                    failing.append(name)
        if failing:
            print(f"  Failing case candidates ({len(failing)}):")
            for c in failing[:10]:
                print(f"    - {c}")

        # Open Question 4j-1: no XDS smoke-history endpoint surfaced via
        # current coding abilities; route operator to XDS UI.
        manual = [
            "Open XDS UI smoke history; identify failing cases.",
            "Follow the Fabric **Master TSG**: "
            "https://eng.ms/docs/cloud-ai-platform/azure-core/azure-storage/"
            "azure-storage-dev-mansah/xstore/xdeployment/xdeployment-tsgs/"
            "stgos/incidents/_master_tsg",
            "If lease owner approves a skip, insert the per-domain row below "
            f"into `{XKULFI_DYNAMIC_SETTING_TABLE}`; do NOT write programmatically.",
            f"Otherwise escalate to "
            f"{ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]} "
            f"(Redmond) or {ESCALATION_CONTACT_SHANGHAI} (Shanghai).",
        ]
        skip_row = self._format_skip_config_row(include_domain=True)
        print(skip_row)
        diagnosis = "No smoke test passed for the configured retry count."
        if failing:
            diagnosis += "\n\nFailing case candidates parsed from logs: " + ", ".join(
                f"`{c}`" for c in failing[:10]
            )
        summary = self._build_evidence_summary(
            "SmokeTestOperation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: ValidateBuildOperation (step-4k) ─────────────

    async def _branch_validate_build(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("ValidateBuildOperation (step-4k)")
        # Best-effort failure-kind classification.
        failure_kind = ""
        joined = " ".join(r.get("message", "") for r in self.failure_logs).lower()
        if "downgrade" in joined:
            failure_kind = "Downgrade"
        elif "empty build" in joined or "emptybuild" in joined:
            failure_kind = "EmptyBuild"
        elif any(r.get("exception_type") for r in self.failure_logs):
            failure_kind = "Exception"
        print(f"  Best-effort failure_kind = {failure_kind or '<unclassified>'}")

        manual = [
            f"If failure_kind is `Downgrade`: follow How to abort an "
            "AppRollout: https://msazure.visualstudio.com/One/_wiki/wikis/"
            "XKulfi/160614/AppRollout-manual-actions?anchor=how-to-abort-an-approllout%3F"
            ". For Preprod personal-test downgrade, confirm with the tenant owner.",
            f"If failure_kind is `EmptyBuild` and the tenant is in a newly-"
            f"added cluster, ask {ESCALATION_CONTACT_SHANGHAI} to follow up "
            "with the OM team.",
            "If failure_kind is `Exception`: file a bug against the build/"
            "validation owners.",
            f"Last-resort skip (lease-owner approval): insert the row below "
            f"into `{XKULFI_DYNAMIC_SETTING_TABLE}`; do NOT write programmatically.",
        ]
        skip_row = self._format_skip_config_row()
        print(skip_row)
        diagnosis = (
            "Pre-rollout build validation failed."
            + (f" Best-effort failure_kind: `{failure_kind}`." if failure_kind else "")
        )
        summary = self._build_evidence_summary(
            "ValidateBuildOperation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: ValidateRolloutEntityOperation (step-4l) ─────

    async def _branch_validate_rollout_entity(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("ValidateRolloutEntityOperation (step-4l)")
        ve_name = (self.app or "").lstrip("APP~") or "<UnknownVE>"
        print(f"  Extracted ve_name = {ve_name}")
        manual = [
            f"Open a PR against `Azure-Gold-Config`: edit the `XStore-Global` "
            f"VE → `environment.ini` → `Orchestration` section to add "
            f"`PreSelection`, `CheckFailingLimit`, `MaxScaleUnits`, "
            f"`BatchSize`, `MaxBatchSize`, `SuccessThreshold`, "
            f"`FailureThreshold`, `RolloutCompletionThreshold` for VE "
            f"`{ve_name}`. Sample PR: "
            "https://dev.azure.com/azureconfig/Gold/_git/Azure-Gold-Config/pullrequest/941797",
            "Open a PR against `Storage-XKulfi`: edit "
            "`StorageTenantGroupSettings.xml` → "
            f"`ValidateRolloutEntityOperation.AllowedDeploymentEntities` to "
            f"append VE `{ve_name}`. The XML file is **signed** — follow the "
            "signing workflow. Sample PR: "
            "https://msazure.visualstudio.com/One/_git/Storage-XKulfi/pullrequest/13841810",
            "After both PRs merge and data deployment completes, XKulfi "
            "auto-mitigates this incident. **Do not open the PRs programmatically.**",
        ]
        # No DynamicSettingConfig skip-row for this branch — mitigation is via PRs.
        diagnosis = (
            f"A new VE/PE (`{ve_name}`) is not configured for rollout; "
            "two repo PRs are required (Azure-Gold-Config + Storage-XKulfi)."
        )
        summary = self._build_evidence_summary(
            "ValidateRolloutEntityOperation", diagnosis, manual,
        )
        await self._post_evidence(tsg_input, summary)

    # ── Branch: generic escalation (step-4z) ─────────────────

    async def _branch_generic(
        self, tsg_input: XKulfiUpgradeActionFailureInput,
    ) -> None:
        self._print_banner("Generic escalation (step-4z)")

        # Render a generic skip-row template if we know enough to do so.
        skip_row = None
        if self.operation:
            skip_row = self._format_skip_config_row(
                include_domain=bool(self.domain),
            )
            print(skip_row)

        manual = [
            "This operation is not covered by a dedicated branch in the "
            "TSG (or the title could not be parsed). Triage manually.",
            f"Page `{ESCALATION_TEAM_REDMOND[0]}/{ESCALATION_TEAM_REDMOND[1]}` "
            f"oncall during Redmond hours; otherwise notify "
            f"`{ESCALATION_CONTACT_SHANGHAI}` (Shanghai).",
            "Use the DGrep link and the blob history path in the Evidence "
            "section as the starting point.",
            "If a skip is approved, insert the row below; do NOT write "
            "programmatically.",
        ]
        diagnosis = (
            f"No dedicated branch for operation `{self.operation or '<unparsed>'}` — "
            "escalating with the parsed metadata and DGrep link as evidence."
        )
        summary = self._build_evidence_summary(
            "Generic escalation", diagnosis, manual, skip_row,
        )
        await self._post_evidence(tsg_input, summary)
