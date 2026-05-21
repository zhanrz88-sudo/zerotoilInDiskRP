"""Get Subscription Settings TSG.

Retrieves DiskRP subscription settings for a given subscription and region
via the Compute Platform Disks ACIS extension.

Geneva Action:
    Extension: Compute Platform Disks
    Group: Subscription Operations
    OperationId: GetSubscriptionSettings
    Endpoint: Prod

Read-only — works from backend (no JIT required).
"""

import json
from typing import Any

from pydantic import ConfigDict
from xportal import acis, icm

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput


# ── Input / Output models ───────────────────────────────────


class GetSubscriptionSettingsInput(TsgInput):
    """Input for Get Subscription Settings TSG."""

    model_config = ConfigDict(extra="forbid")

    subscription_id: str
    region: str = ""  # ARM-cased region (e.g. WestUS3). Empty = default.
    api_version: str = ""


class GetSubscriptionSettingsOutput(TsgOutput):
    """Output from Get Subscription Settings TSG."""

    model_config = ConfigDict(extra="forbid")

    settings: dict = {}
    raw_result: str = ""
    status: str = ""  # completed / failed


# ── Constants ────────────────────────────────────────────────

ACIS_EXTENSION = "Compute Platform Disks"
ACIS_OPERATION = "GetSubscriptionSettings"


# ── TSG class ────────────────────────────────────────────────


class GetSubscriptionSettings(TsgBase):
    """Get DiskRP subscription settings for a subscription/region.

    Steps:
        1. Validate input parameters
        2. Execute GetSubscriptionSettings Geneva Action
        3. Post results to ICM incident (if incident_id provided)
    """

    input_type = GetSubscriptionSettingsInput
    output_type = GetSubscriptionSettingsOutput

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> GetSubscriptionSettingsInput:
        """Extract parameters from incident."""
        print(f"Incident: {incident.Title}")
        print(f"Severity: {incident.Severity}")
        print()
        print("=" * 60)
        print("MANUAL INPUT REQUIRED")
        print("This TSG requires subscription ID and region.")
        print("Please use GetSubscriptionSettingsInput directly with run().")
        print("=" * 60)
        raise ValueError(
            "GetSubscriptionSettings requires manual parameter input. "
            "Use tsg.run(GetSubscriptionSettingsInput(...)) with explicit parameters."
        )

    async def _run(
        self, tsg_input: GetSubscriptionSettingsInput,
    ) -> GetSubscriptionSettingsOutput:
        # Step 1: Validate
        await self._step1_validate(tsg_input)

        # Step 2: Execute
        settings, raw = await self._step2_execute(tsg_input)

        # Step 3: Post to ICM
        await self._step3_post_results(tsg_input, raw)

        return GetSubscriptionSettingsOutput(
            settings=settings,
            raw_result=raw[:5000],
            status="completed",
        )

    async def _step1_validate(self, tsg_input: GetSubscriptionSettingsInput):
        """Validate input parameters."""
        print("Step 1: Validating input parameters")
        print(f"  SubscriptionId: {tsg_input.subscription_id}")
        print(f"  Region:         {tsg_input.region or '(default)'}")
        print(f"  ApiVersion:     {tsg_input.api_version or '(latest)'}")

        if not tsg_input.subscription_id:
            raise ValueError("SubscriptionId is required")

        print("  -> Parameters validated.")

    async def _step2_execute(self, tsg_input: GetSubscriptionSettingsInput) -> tuple:
        """Execute GetSubscriptionSettings Geneva Action."""
        print()
        print("Step 2: Executing GetSubscriptionSettings")
        print(f"  Extension:  {ACIS_EXTENSION}")
        print(f"  Operation:  {ACIS_OPERATION}")

        params = [
            tsg_input.subscription_id,
            tsg_input.region,
            tsg_input.api_version,
        ]

        if self.dry_run:
            print()
            print(f"  [DRY-RUN] Would call:")
            print(f"    acis.execute('{ACIS_EXTENSION}', '{ACIS_OPERATION}', {params}, endpoint='Prod')")
            return {}, "dry-run-skipped"

        r = await acis.execute(
            ACIS_EXTENSION,
            ACIS_OPERATION,
            params,
            endpoint="Prod",
        )
        msg = r.get("resultMessage", "") if isinstance(r, dict) else str(r)

        try:
            settings = json.loads(msg)
            print(f"  -> Success. Parsed {len(settings)} top-level keys.")
            print(json.dumps(settings, indent=2))
            return settings, msg
        except Exception:
            print(f"  -> Raw result (non-JSON):")
            print(f"  {msg[:2000]}")
            return {}, msg

    async def _step3_post_results(self, tsg_input: GetSubscriptionSettingsInput, raw: str):
        """Post results to ICM incident."""
        print()
        print("Step 3: Posting results to ICM")

        if not tsg_input.incident_id or tsg_input.incident_id == "0":
            print("  (No incident ID — skipping ICM update)")
            return

        comment = (
            f"<h3>GetSubscriptionSettings - Results</h3>"
            f"<p><b>SubscriptionId:</b> <code>{tsg_input.subscription_id}</code></p>"
            f"<p><b>Region:</b> <code>{tsg_input.region or 'default'}</code></p>"
            f"<pre>{raw[:3000]}</pre>"
        )

        if self.dry_run:
            print(f"  [DRY-RUN] Would post to ICM: {comment[:200]}...")
            return

        incident = await icm.get_incident(int(tsg_input.incident_id))
        await incident.add_description(comment, is_html=True)
        print("  -> Results posted to ICM.")
