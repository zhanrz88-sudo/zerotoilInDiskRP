"""Approve SnapshotImmutabilityPolicyPreview Feature Registration TSG.

Simple TSG that approves the SnapshotImmutabilityPolicyPreview feature flag
for a given subscription via the Azure Resource Manager ACIS extension.

Geneva Action:
    Extension: Azure Resource Manager
    Group: Feature Management
    OperationId: ApproveFeatureRegistration
    Endpoint: Feature

Required Claims: Unknown (likely ARM-level, not DiskRP)
"""

import json
from typing import Any

from pydantic import ConfigDict
from xportal import acis, icm

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput


# ── Input / Output models ───────────────────────────────────


class ApproveFeatureInput(TsgInput):
    """Input for Approve Feature Registration TSG."""

    model_config = ConfigDict(extra="forbid")

    subscription_id: str


class ApproveFeatureOutput(TsgOutput):
    """Output from Approve Feature Registration TSG."""

    model_config = ConfigDict(extra="forbid")

    result_message: str = ""
    status: str = ""  # completed / failed


# ── Constants ────────────────────────────────────────────────

ACIS_EXTENSION = "Azure Resource Manager"
ACIS_OPERATION = "ApproveFeatureRegistration"
ACIS_ENDPOINT = "Feature"
RESOURCE_PROVIDER = "Microsoft.Compute"
FEATURE_NAME = "SnapshotImmutabilityPolicyPreview"


# ── TSG class ────────────────────────────────────────────────


class ApproveSnapshotImmutabilityFeature(TsgBase):
    """Approve SnapshotImmutabilityPolicyPreview for a subscription.

    Steps:
        1. Validate subscription ID
        2. Execute ApproveFeatureRegistration Geneva Action
        3. Post results to ICM incident
    """

    input_type = ApproveFeatureInput
    output_type = ApproveFeatureOutput

    result_message: str = ""

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> ApproveFeatureInput:
        """Extract subscription ID from incident.

        This TSG requires manual subscription ID input.
        """
        print(f"Incident: {incident.Title}")
        print(f"Severity: {incident.Severity}")
        print()
        print("=" * 60)
        print("MANUAL INPUT REQUIRED")
        print("Please provide the subscription ID.")
        print("Use: tsg.run(ApproveFeatureInput(subscription_id='...'))")
        print("=" * 60)
        raise Exception(
            "Subscription ID must be provided manually. "
            "Use tsg.run(ApproveFeatureInput(subscription_id='...', incident_id='...'))."
        )

    async def _run(self, tsg_input: ApproveFeatureInput) -> ApproveFeatureOutput:
        # Step 1: Validate
        await self._step1_validate(tsg_input)

        # Step 2: Execute Geneva Action
        await self._step2_approve(tsg_input)

        # Step 3: Post to ICM
        await self._step3_post_results(tsg_input)

        return ApproveFeatureOutput(
            result_message=self.result_message,
            status="completed" if self.result_message else "failed",
        )

    async def _step1_validate(self, tsg_input: ApproveFeatureInput):
        """Validate subscription ID format."""
        print("Step 1: Validating input")
        print(f"  SubscriptionId: {tsg_input.subscription_id}")
        print(f"  Feature:        {RESOURCE_PROVIDER}/{FEATURE_NAME}")

        sub = tsg_input.subscription_id.strip()
        if len(sub) != 36 or sub.count("-") != 4:
            raise ValueError(f"Invalid subscription ID format: {sub}")
        print("  ✓ Subscription ID format valid")

    async def _step2_approve(self, tsg_input: ApproveFeatureInput):
        """Execute ApproveFeatureRegistration via ACIS."""
        print(f"\nStep 2: Approving {FEATURE_NAME} for {tsg_input.subscription_id}")

        params = [
            RESOURCE_PROVIDER,          # resourceprovidernamespace
            FEATURE_NAME,               # featurename
            tsg_input.subscription_id,  # wellknownsubscriptionid
        ]

        if self.dry_run:
            print(f"  [DRY-RUN] Would call: acis.execute(")
            print(f"      '{ACIS_EXTENSION}', '{ACIS_OPERATION}',")
            print(f"      {params},")
            print(f"      endpoint='{ACIS_ENDPOINT}')")
            self.result_message = "dry-run-skipped"
            return

        result = await acis.execute(
            ACIS_EXTENSION,
            ACIS_OPERATION,
            params,
            endpoint=ACIS_ENDPOINT,
        )

        if isinstance(result, dict):
            self.result_message = result.get("resultMessage", json.dumps(result))
        else:
            self.result_message = str(result)

        print(f"  ✓ Result: {self.result_message[:200]}")

    async def _step3_post_results(self, tsg_input: ApproveFeatureInput):
        """Post approval result to ICM incident."""
        print(f"\nStep 3: Posting results to ICM")

        if not tsg_input.incident_id or tsg_input.incident_id == "0":
            print("  (No incident ID — skipping ICM update)")
            return

        if self.dry_run:
            print(f"  [DRY-RUN] Would post to incident {tsg_input.incident_id}")
            return

        note = (
            f"**Feature Registration Approved**\n\n"
            f"- Feature: `{RESOURCE_PROVIDER}/{FEATURE_NAME}`\n"
            f"- Subscription: `{tsg_input.subscription_id}`\n"
            f"- Result: {self.result_message[:500]}\n\n"
            f"Approved via automated TSG (ZeroToil)."
        )

        await icm.add_note(tsg_input.incident_id, note)
        print(f"  ✓ Posted to incident {tsg_input.incident_id}")
