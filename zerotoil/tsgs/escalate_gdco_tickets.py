"""Escalate GDCO Tickets TSG.

Generated from: zero-toil/tsgs/escalate-gdco-tickets/escalate-gdco-tickets.md
Source: https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Escalate%20GDCO%20Tickets.md
"""

from typing import Optional

from pydantic import ConfigDict
from xportal import acis

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput


class ManualActionRequired(Exception):
    """Raised when a TSG step requires human intervention."""


# ── Input / Output models ───────────────────────────────────


class EscalateGdcoTicketsInput(TsgInput):
    """Input for Escalate GDCO Tickets TSG."""

    model_config = ConfigDict(extra='forbid')

    gdco_ticket_id: Optional[str] = None
    target_severity: str  # "Sev2" or "Sev3-Expedite"
    node_id: str
    fault_description: str


class EscalateGdcoTicketsOutput(TsgOutput):
    """Output from Escalate GDCO Tickets TSG."""

    model_config = ConfigDict(extra='forbid')

    gdco_ticket_id: str = ""
    escalation_result: str = ""  # sev2_escalated / sev3_expedited / ticket_linked


# ── TSG class ────────────────────────────────────────────────


class EscalateGdcoTickets(TsgBase):
    """Escalate a GDCO datacenter ticket to get hardware repairs prioritized.

    Steps:
        1. Link or create GDCO ticket (manual — ICM UI only)
        2. Escalate based on target severity (Sev2 manual, Sev3-Expedite via Geneva Action)
    """

    input_type = EscalateGdcoTicketsInput
    output_type = EscalateGdcoTicketsOutput

    # intermediate state
    gdco_ticket_id: str = ""
    escalation_result: str = ""

    async def _run(self, tsg_input: EscalateGdcoTicketsInput) -> EscalateGdcoTicketsOutput:
        await self.run_step(self._step_1_link_or_create_ticket, tsg_input)
        await self.run_step(self._step_2_escalate_ticket, tsg_input)

        return EscalateGdcoTicketsOutput(
            gdco_ticket_id=self.gdco_ticket_id,
            escalation_result=self.escalation_result,
        )

    # ── Step 1 ───────────────────────────────────────────────

    def _step_1_link_or_create_ticket(
        self, tsg_input: EscalateGdcoTicketsInput
    ) -> None:
        """Link or create GDCO ticket via ICM portal.

        AUTOMATABLE: No — GDCO ticket creation/linking is ICM UI only.
        """
        if tsg_input.gdco_ticket_id:
            self.gdco_ticket_id = tsg_input.gdco_ticket_id
            print(f"Using existing GDCO ticket: {self.gdco_ticket_id}")
            return

        # TODO: Open Question — Can GDCO tickets be created programmatically?
        print("=" * 60)
        print("MANUAL ACTION REQUIRED: Link or create GDCO ticket")
        print(f"  1. Open ICM incident {tsg_input.incident_id}")
        print("  2. Go to Mitigation and Resolution tab")
        print("  3. Link existing GDCO ticket OR create a new one")
        print(f"  4. Node: {tsg_input.node_id}")
        print(f"  5. Description: {tsg_input.fault_description}")
        print("  6. Click Save")
        print("=" * 60)
        raise ManualActionRequired(
            "GDCO ticket must be created/linked manually via ICM portal"
        )

    # ── Step 2 ───────────────────────────────────────────────

    async def _step_2_escalate_ticket(
        self, tsg_input: EscalateGdcoTicketsInput
    ) -> None:
        """Escalate GDCO ticket based on target severity.

        - Sev2: Manual — requires DRI on bridge.
        - Sev3-Expedite: Automatable via Geneva Action GDCOChangeSeverity.
        """
        if tsg_input.target_severity == "Sev2":
            self._escalate_to_sev2(tsg_input)
        elif tsg_input.target_severity == "Sev3-Expedite":
            await self._escalate_sev3_expedite(tsg_input)
        else:
            raise ValueError(
                f"Unknown target_severity: {tsg_input.target_severity}"
            )

    def _escalate_to_sev2(self, tsg_input: EscalateGdcoTicketsInput) -> None:
        """Sev2 escalation requires DRI on bridge — not automatable."""
        print("=" * 60)
        print("MANUAL ACTION REQUIRED: Escalate GDCO ticket to Sev2")
        print(f"  GDCO Ticket: {self.gdco_ticket_id}")
        print("  1. Navigate to the GDCO ticket")
        print("  2. Click severity circle → change to Sev2 → Save")
        print("  3. A DRI MUST be on the bridge for the entire duration")
        print("  4. An email from OMC will confirm impact")
        print("=" * 60)
        raise ManualActionRequired(
            "Sev2 GDCO escalation requires DRI on bridge — manual action"
        )

    async def _escalate_sev3_expedite(
        self, tsg_input: EscalateGdcoTicketsInput
    ) -> None:
        """Sev3 Expedite via Geneva Action GDCOChangeSeverity."""
        print(f"Executing GDCOChangeSeverity for ticket {self.gdco_ticket_id}")
        await acis.execute(
            extension_name="Sustainability Operations - Safe",
            operation_id="GDCOChangeSeverity",
            params=[
                tsg_input.incident_id,       # Incident ID
                self.gdco_ticket_id,          # GDCO Ticket ID
                "3",                          # Severity
                "true",                       # Expedite Ticket
            ],
        )
        self.escalation_result = "sev3_expedited"
        print(f"GDCO ticket {self.gdco_ticket_id} expedited (Sev3-Expedite)")
        print("SLA: 24 hours. If no response, contact mastange@, margs@")
