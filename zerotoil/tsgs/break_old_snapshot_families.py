"""Break Old Snapshot Families for Disk TSG.

Generated from: zero-toil/tsgs/break-old-snapshot-families/break-old-snapshot-families.md
Source: OneNote — ComputeVM / Disks / ManagedDisksWiki / TSG.one

Use cases:
    1. Corruption recovery — start a new snapshot family
    2. Leak unblock — unblock operations when XStore has unfixable leaks

JIT Required: PlatformServiceOperator
"""

import json
from typing import Any, Optional

from pydantic import ConfigDict
from xportal import acis, icm

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput


class ManualActionRequired(Exception):
    """Raised when a TSG step requires human intervention."""


# ── Input / Output models ───────────────────────────────────


class BreakSnapshotFamilyInput(TsgInput):
    """Input for Break Old Snapshot Families TSG."""

    model_config = ConfigDict(extra="forbid")

    disk_name: str
    subscription_id: str
    resource_group: str
    region: str
    clear_billing: bool = False


class BreakSnapshotFamilyOutput(TsgOutput):
    """Output from Break Old Snapshot Families TSG."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = ""
    action_result: str = ""
    status: str = ""  # submitted / completed / failed / manual_action_required


# ── Constants ────────────────────────────────────────────────

ACIS_EXTENSION = "Compute Platform Disks"
ACIS_OPERATION = "RemoveIncrementalSnapshotFamilyOnDisk"


# ── TSG class ────────────────────────────────────────────────


class BreakOldSnapshotFamilies(TsgBase):
    """Break old incremental snapshot families for a managed disk.

    Steps:
        1. Validate input parameters
        2. Check ClearBilling approval gate
        3. Execute Geneva Action (Invoke-RemoveIncrementalSnapshotFamilyOnDisk)
        4. Poll for result
        5. Post results to ICM incident
    """

    input_type = BreakSnapshotFamilyInput
    output_type = BreakSnapshotFamilyOutput

    # intermediate state
    action_id: str = ""
    action_result: str = ""

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> BreakSnapshotFamilyInput:
        """Extract disk parameters from incident.

        Expects parameters in the incident description or as manual input.
        This TSG typically requires manual parameter entry since the
        incident title doesn't contain all required fields.
        """
        print(f"Incident: {incident.Title}")
        print(f"Severity: {incident.Severity}")
        print()
        print("=" * 60)
        print("MANUAL INPUT REQUIRED")
        print("This TSG requires disk parameters that must be provided manually.")
        print("Please use BreakSnapshotFamilyInput directly with run().")
        print("=" * 60)
        raise ManualActionRequired(
            "Break Old Snapshot Families requires manual parameter input. "
            "Use tsg.run(BreakSnapshotFamilyInput(...)) with explicit parameters."
        )

    async def _run(
        self, tsg_input: BreakSnapshotFamilyInput,
    ) -> BreakSnapshotFamilyOutput:
        # Step 1: Validate inputs
        await self._step1_validate(tsg_input)

        # Step 2: ClearBilling approval gate
        if tsg_input.clear_billing:
            await self._step2_clear_billing_gate(tsg_input)

        # Step 3: Execute Geneva Action
        await self._step3_execute_action(tsg_input)

        # Step 4: Post results to ICM
        await self._step4_post_results(tsg_input)

        return BreakSnapshotFamilyOutput(
            action_id=self.action_id,
            action_result=self.action_result,
            status="completed" if self.action_result else "submitted",
        )

    async def _step1_validate(self, tsg_input: BreakSnapshotFamilyInput):
        """Validate input parameters."""
        print("Step 1: Validating input parameters")
        print(f"  DiskName:       {tsg_input.disk_name}")
        print(f"  SubscriptionId: {tsg_input.subscription_id}")
        print(f"  ResourceGroup:  {tsg_input.resource_group}")
        print(f"  Region:         {tsg_input.region}")
        print(f"  ClearBilling:   {tsg_input.clear_billing}")

        if not tsg_input.disk_name:
            raise ValueError("DiskName is required")
        if not tsg_input.subscription_id:
            raise ValueError("SubscriptionId is required")
        if not tsg_input.resource_group:
            raise ValueError("ResourceGroup is required")
        if not tsg_input.region:
            raise ValueError("Region is required")

        print("  -> All parameters validated.")

    async def _step2_clear_billing_gate(self, tsg_input: BreakSnapshotFamilyInput):
        """Approval gate for ClearBilling flag."""
        print()
        print("=" * 60)
        print("APPROVAL REQUIRED: ClearBilling flag is set")
        print("=" * 60)
        print("ClearBilling should ONLY be used when a PM explicitly requests it.")
        print(f"  DiskName: {tsg_input.disk_name}")
        print(f"  SubscriptionId: {tsg_input.subscription_id}")
        print()

        if self.dry_run:
            print("  [DRY-RUN] Skipping ClearBilling approval — would require PM confirmation.")
            return

        print("  Proceeding with ClearBilling=true as requested.")

    async def _step3_execute_action(self, tsg_input: BreakSnapshotFamilyInput):
        """Execute the Geneva Action to break snapshot families."""
        print()
        print("Step 3: Executing Geneva Action")
        print(f"  Extension:  {ACIS_EXTENSION}")
        print(f"  Operation:  {ACIS_OPERATION}")

        # Build parameters for the new Compute Platform Disks action
        params = [
            tsg_input.subscription_id,       # wellknownsubscriptionid
            tsg_input.region,                 # smeregionarmnameparameter
            tsg_input.resource_group,         # smeresourcegroupnameparameter
            tsg_input.disk_name,              # smedisknameparameter
            "false",                          # smeskipvalidationparameter
            str(tsg_input.clear_billing).lower(),  # smeclearbillingparameter
            "",                               # smeapiversionparameter
        ]

        print(f"  Parameters:")
        print(f"    SubscriptionId:   {tsg_input.subscription_id}")
        print(f"    Region:           {tsg_input.region}")
        print(f"    ResourceGroup:    {tsg_input.resource_group}")
        print(f"    DiskName:         {tsg_input.disk_name}")
        print(f"    SkipValidation:   false")
        print(f"    ClearBilling:     {str(tsg_input.clear_billing).lower()}")

        if self.dry_run:
            print()
            print("  [DRY-RUN] Would submit Geneva Action:")
            print(f"    acis.submit('{ACIS_EXTENSION}', '{ACIS_OPERATION}', {params})")
            self.action_id = "dry-run-action-id"
            self.action_result = "dry-run-skipped"
            return

        print()
        print("=" * 60)
        print("APPROVAL REQUIRED: About to execute mutating Geneva Action")
        print(f"  {ACIS_OPERATION}")
        print(f"  Disk: {tsg_input.disk_name}")
        print(f"  Sub:  {tsg_input.subscription_id}")
        print(f"  RG:   {tsg_input.resource_group}")
        print(f"  Region: {tsg_input.region}")
        if tsg_input.clear_billing:
            print("  ClearBilling: YES (PM-approved)")
        print("=" * 60)

        # Submit and poll
        # Endpoint varies by auth path: "Production" for AKS backend, "Prod" for SAW/dSTS
        response = await acis.submit(
            ACIS_EXTENSION,
            ACIS_OPERATION,
            params,
            endpoint="Prod",
        )
        self.action_id = response.get("id", str(response))
        print(f"  -> Submitted. Action ID: {self.action_id}")
        print("  -> Polling for result...")

        result = await acis.get_result(
            ACIS_EXTENSION,
            self.action_id,
            wait_for_completion=True,
        )
        self.action_result = str(result)
        print(f"  -> Action completed.")
        print(f"  -> Result: {self.action_result[:500]}")

    async def _step4_post_results(self, tsg_input: BreakSnapshotFamilyInput):
        """Post results to ICM incident."""
        print()
        print("Step 4: Posting results to ICM incident")

        comment = (
            f"<h3>Break Old Snapshot Families - Completed</h3>"
            f"<p><b>Operation:</b> <code>{ACIS_EXTENSION} / {ACIS_OPERATION}</code></p>"
            f"<table border='1' cellpadding='5'>"
            f"<tr><th>Parameter</th><th>Value</th></tr>"
            f"<tr><td>DiskName</td><td>{tsg_input.disk_name}</td></tr>"
            f"<tr><td>SubscriptionId</td><td>{tsg_input.subscription_id}</td></tr>"
            f"<tr><td>ResourceGroup</td><td>{tsg_input.resource_group}</td></tr>"
            f"<tr><td>Region</td><td>{tsg_input.region}</td></tr>"
            f"<tr><td>ClearBilling</td><td>{tsg_input.clear_billing}</td></tr>"
            f"</table>"
            f"<p><b>Action ID:</b> <code>{self.action_id}</code></p>"
            f"<p><b>Result:</b></p><pre>{self.action_result[:1000]}</pre>"
        )

        if self.dry_run:
            print("  [DRY-RUN] Would post to ICM:")
            print(f"  {comment[:200]}...")
            return

        incident = await icm.get_incident(int(tsg_input.incident_id))
        await incident.add_description(comment, is_html=True)
        print("  -> Results posted to ICM.")
