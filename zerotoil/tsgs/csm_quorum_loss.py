"""CSM 2 Failures Away from Quorum Loss TSG.

Generated from: zero-toil/tsgs/csm-quorum-loss/csm-2-failures-from-quorum-loss.md
Source: https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/CSM%20Quorum%20Loss%20TSG.md
"""

from typing import Optional

from pydantic import ConfigDict
from xds_client import ApiClient, RoleInstancesApi, UpgradeStateApi
from xds_client.models import PingRequestParams
from xportal import icm, kusto

from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput
from zerotoil.tsgs.escalate_gdco_tickets import (
    EscalateGdcoTickets,
    EscalateGdcoTicketsInput,
)


class ManualActionRequired(Exception):
    """Raised when a TSG step requires human intervention."""


# ── Input / Output models ───────────────────────────────────


class Csm2FailuresFromQuorumLossInput(TsgInput):
    """Input for CSM 2 Failures Away from Quorum Loss TSG.

    Entry-level TSG: incident_id comes from TsgInput base.
    Additional context is extracted from the incident during Step 1.
    """

    model_config = ConfigDict(extra='forbid')

    tenant_name: str
    cloud_environment: str = "Public"  # Public / USSec / USNat


class Csm2FailuresFromQuorumLossOutput(TsgOutput):
    """Output from CSM 2 Failures Away from Quorum Loss TSG."""

    model_config = ConfigDict(extra='forbid')

    offline_csms: list[dict] = []
    deployment_active: bool = False
    node_states: list[dict] = []
    recovery_results: list[dict] = []
    escalation_needed: bool = False


# ── Kusto endpoint mapping ──────────────────────────────────

_KUSTO_ENDPOINTS = {
    "Public": ("https://xsse.kusto.windows.net", "xssedb"),
    "USSec": ("https://xsse.ussecwest.kusto.microsoft.scloud", "xssedb"),
    "USNat": ("https://xsse.usnateast.kusto.eaglex.ic.gov", "xssedb"),
}


# ── TSG class ────────────────────────────────────────────────


class Csm2FailuresFromQuorumLoss(TsgBase):
    """Triage CSM 2 Failures Away from Quorum Loss incidents.

    Steps:
        1. Identify offline CSMs via XDS ping
        2. Check deployment status via XDS upgrade state
        3. Identify node state for each offline CSM via Kusto
        4. Recover nodes by state (HI → Geneva Actions / OFR → GDCO)
        5. Post-mitigation monitoring and follow-up
    """

    input_type = Csm2FailuresFromQuorumLossInput
    output_type = Csm2FailuresFromQuorumLossOutput

    # intermediate state
    offline_csms: list[dict] = []
    deployment_active: bool = False
    deployment_ud: str = ""
    node_states: list[dict] = []
    recovery_results: list[dict] = []
    escalation_needed: bool = False

    async def _run(
        self, tsg_input: Csm2FailuresFromQuorumLossInput
    ) -> Csm2FailuresFromQuorumLossOutput:
        await self.run_step(self._step_1_identify_offline_csms, tsg_input)
        await self.run_step(self._step_2_check_deployment_status, tsg_input)
        await self.run_step(self._step_3_identify_node_state, tsg_input)
        await self.run_step(self._step_4_recover_nodes, tsg_input)
        await self.run_step(self._step_5_post_mitigation, tsg_input)

        return Csm2FailuresFromQuorumLossOutput(
            offline_csms=self.offline_csms,
            deployment_active=self.deployment_active,
            node_states=self.node_states,
            recovery_results=self.recovery_results,
            escalation_needed=self.escalation_needed,
        )

    # ── Step 1 — Identify offline CSMs ───────────────────────

    async def _step_1_identify_offline_csms(
        self, tsg_input: Csm2FailuresFromQuorumLossInput
    ) -> None:
        """Connect to XDS, list CSM role instances, ping all, filter offline.

        Coding ability: xds-api-call (RoleInstancesApi)
        AUTOMATABLE: Yes
        """
        client = ApiClient()
        env = (
            tsg_input.cloud_environment
            if tsg_input.cloud_environment != "Public"
            else None
        )
        await client.connect_tenant(
            tsg_input.tenant_name, environment=env
        )

        api = RoleInstancesApi(api_client=client)

        # List all role instances and filter to CSMs
        all_instances = await api.role_instances_get_role_instances()
        csm_instances = [
            ri for ri in all_instances if ri.role_name == "CSM"
        ]

        if not csm_instances:
            print(f"WARNING: No CSM instances found on {tsg_input.tenant_name}")
            return

        # Ping all CSM instances
        csm_names = [ri.role_instance_name for ri in csm_instances]
        ping_params = PingRequestParams(
            role_instance_names=csm_names,
            request_role_ping=True,
            request_rdma_ping=False,
            request_log_agent_ping=False,
        )
        ping_results = await api.role_instances_ping(ping_params)

        # Build status map
        status_map = {
            pr.role_instance_name: pr.role_status for pr in ping_results
        }

        for ri in csm_instances:
            status = status_map.get(ri.role_instance_name, "Unknown")
            entry = {
                "role_instance_name": ri.role_instance_name,
                "node_id": ri.node_id,
                "update_domain": ri.upgrade_domain,
                "fault_domain": ri.fault_domain,
                "status": status,
            }
            if status != "Responsive":
                self.offline_csms.append(entry)

        print(f"CSM instances on {tsg_input.tenant_name}: "
              f"{len(self.offline_csms)} offline")
        for csm in self.offline_csms:
            print(f"  {csm['role_instance_name']} "
                  f"(node={csm['node_id']}, UD={csm['update_domain']}) "
                  f"— {csm['status']}")

    # ── Step 2 — Check deployment status ─────────────────────

    async def _step_2_check_deployment_status(
        self, tsg_input: Csm2FailuresFromQuorumLossInput
    ) -> None:
        """Query upgrade state to check for active deployments.

        Coding ability: xds-api-call (UpgradeStateApi)
        AUTOMATABLE: Yes
        """
        client = ApiClient()
        env = (
            tsg_input.cloud_environment
            if tsg_input.cloud_environment != "Public"
            else None
        )
        await client.connect_tenant(
            tsg_input.tenant_name, environment=env
        )

        api = UpgradeStateApi(api_client=client)
        state = await api.upgrade_state_get_upgrade_state()

        if state and state.upgrade_status and "In Progress" in state.upgrade_status:
            self.deployment_active = True
            self.deployment_ud = getattr(state, "current_ud", "")
            print(f"Active deployment detected: UD={self.deployment_ud}")
        else:
            self.deployment_active = False
            print("No active deployment")

        if self.deployment_active:
            # Check UD overlap with offline CSMs
            offline_uds = {csm["update_domain"] for csm in self.offline_csms}
            if self.deployment_ud in offline_uds:
                print(f"WARNING: Deployment UD {self.deployment_ud} overlaps "
                      f"with offline CSM UDs")
                # TODO: Open Question — auto-determine ICM severity
                # for Sev2 (1 away): contact xdep@microsoft.com to block upgrade
                # for Sev3 (2 away): continue repairs, avoid active UD/FD

    # ── Step 3 — Identify node state ─────────────────────────

    async def _step_3_identify_node_state(
        self, tsg_input: Csm2FailuresFromQuorumLossInput
    ) -> None:
        """Query Kusto for fabric state of each offline CSM node.

        Coding ability: kusto-query (GetAllStorageNodeFabricHealth)
        AUTOMATABLE: Yes
        """
        cluster_uri, database = _KUSTO_ENDPOINTS.get(
            tsg_input.cloud_environment,
            _KUSTO_ENDPOINTS["Public"],
        )

        for csm in self.offline_csms:
            node_id = csm["node_id"]

            kql = f"""
GetAllStorageNodeFabricHealth
| where NodeId contains "{node_id}"
| project ClusterId, Tenant, NodeId, TMState, DCMState,
          HIFault, HIFaultReason, HIFaultTime,
          OFRFaultCode, OFRFaultReason
""".strip()

            # TODO: Open Question — How stale is Kusto data? (minutes? hours?)
            result = await kusto.query(cluster_uri, database, kql)
            df = result.to_df()

            node_state = "Unknown"
            fault_code = ""
            fault_reason = ""

            if not df.empty:
                row = df.iloc[0]
                tm_state = str(row.get("TMState", ""))
                if "HumanInvestigate" in tm_state:
                    node_state = "HI"
                    fault_code = str(row.get("HIFault", ""))
                    fault_reason = str(row.get("HIFaultReason", ""))
                elif "OutForRepair" in tm_state:
                    node_state = "OFR"
                    fault_code = str(row.get("OFRFaultCode", ""))
                    fault_reason = str(row.get("OFRFaultReason", ""))
                elif "Ready" in tm_state:
                    node_state = "Ready"
                else:
                    node_state = tm_state
            else:
                # Kusto returned nothing — warn about stale data
                print(f"  WARNING: No Kusto data for node {node_id}. "
                      f"Data may be stale. Recommend FcShell verification.")

            state_entry = {
                "node_id": node_id,
                "role_instance_name": csm["role_instance_name"],
                "node_state": node_state,
                "fault_code": fault_code,
                "fault_reason": fault_reason,
            }
            self.node_states.append(state_entry)

            print(f"  Node {node_id}: {node_state} "
                  f"(FC={fault_code}, reason={fault_reason})")

    # ── Step 4 — Recover nodes by state ──────────────────────

    async def _step_4_recover_nodes(
        self, tsg_input: Csm2FailuresFromQuorumLossInput
    ) -> None:
        """For each offline CSM, apply recovery action based on state.

        - HI: Calls storage-node-recovery TSG (separate folder)
        - OFR: Calls escalate-gdco-tickets TSG (separate folder)
        - Ready: Escalate to XSSE FTE
        - Other: Wait

        Coding ability: geneva-action-call, xds-api-call
        AUTOMATABLE: Partially
        """
        for node in self.node_states:
            state = node["node_state"]
            node_id = node["node_id"]

            if state == "HI":
                result = self._recover_hi_node(tsg_input, node)
            elif state == "OFR":
                result = await self._recover_ofr_node(tsg_input, node)
            elif state == "Ready":
                result = await self._handle_ready_but_offline(tsg_input, node)
            else:
                result = {
                    "node_id": node_id,
                    "action": "waiting",
                    "outcome": "Node in unexpected state, waiting for "
                               "it to fault or recover",
                }
                print(f"  Node {node_id}: state={state}, waiting...")

            self.recovery_results.append(result)

    def _recover_hi_node(
        self,
        tsg_input: Csm2FailuresFromQuorumLossInput,
        node: dict,
    ) -> dict:
        """HI node recovery: try storage-node-recovery TSG, then generic."""
        node_id = node["node_id"]
        fault_code = node.get("fault_code", "")

        # Known fault codes that have dedicated TSGs
        known_fcs = {"8", "70007", "43030"}

        if fault_code in known_fcs:
            # Call storage-node-recovery TSG
            # TODO: Generate storage_node_recovery.py and import it
            print(f"  Node {node_id}: HI with FC {fault_code}")
            print("=" * 60)
            print("MANUAL ACTION REQUIRED: Follow Storage Node Recovery TSG")
            print(f"  Fault code: {fault_code}")
            print(f"  See: ../storage-node-recovery/storage-node-recovery.md")
            print("  Then: ../storage-node-recovery-fc-"
                  f"{fault_code}/fc-{fault_code}-node-recovery.md")
            print("=" * 60)
            raise ManualActionRequired(
                f"Storage Node Recovery for FC {fault_code} "
                f"requires manual execution — see TSG"
            )

        # Generic HI recovery: Reset Health → Power Cycle → Escalate
        return self._generic_hi_recovery(tsg_input, node)

    def _generic_hi_recovery(
        self,
        tsg_input: Csm2FailuresFromQuorumLossInput,
        node: dict,
    ) -> dict:
        """Generic HI recovery: Reset Health, then Power Cycle + Reset.

        Coding ability: geneva-action-call
        AUTOMATABLE: Partially (requires human approval for Geneva Actions)

        # APPROVAL_GATE: Geneva Actions require human confirmation
        """
        node_id = node["node_id"]
        print(f"  Node {node_id}: Attempting generic HI recovery")

        # APPROVAL_GATE: confirm before executing Geneva Actions
        print("=" * 60)
        print("APPROVAL REQUIRED: Execute Geneva Actions for node recovery")
        print(f"  Node: {node_id}")
        print(f"  Tenant: {tsg_input.tenant_name}")
        print("  Actions: ResetNodeHealth → PowerCycle → ResetNodeHealth")
        print("  Prerequisite: JIT FFE/PlatformAdministrator")
        print("=" * 60)
        raise ManualActionRequired(
            f"Geneva Actions for HI node {node_id} require human approval. "
            f"Execute ResetNodeHealthWithSafetyChecksCrossServiceDelegated "
            f"and PowerNodeWithSafetyChecksDelegated via Geneva Actions portal."
        )

    async def _recover_ofr_node(
        self,
        tsg_input: Csm2FailuresFromQuorumLossInput,
        node: dict,
    ) -> dict:
        """OFR node: escalate GDCO ticket."""
        node_id = node["node_id"]

        if tsg_input.cloud_environment != "Public":
            # AGC: annotate ICM and escalate to xsse-tented@
            self.escalation_needed = True
            print(f"  Node {node_id}: OFR in AGC — annotating ICM "
                  f"and escalating to xsse-tented@microsoft.com")
            await self._annotate_incident(
                tsg_input,
                f"Node {node_id} is in OFR state. "
                f"FC={node.get('fault_code', 'N/A')}. "
                f"Escalating to xsse-tented@microsoft.com for AGC recovery.",
            )
            return {
                "node_id": node_id,
                "action": "escalated_agc",
                "outcome": "Annotated ICM and escalated to xsse-tented@",
            }

        # Public: call escalate-gdco-tickets TSG
        # TODO: Open Question — How to check if a GDCO ticket already
        # exists for a node programmatically?
        fault_desc = (
            f"Storage node {node_id} on {tsg_input.tenant_name} is in OFR. "
            f"Fault: {node.get('fault_code', 'N/A')} - "
            f"{node.get('fault_reason', 'N/A')}. "
            f"Please prioritize repair."
        )

        # Determine target severity
        # TODO: Open Question — Exact CSM quorum threshold per tenant
        target_sev = "Sev3-Expedite"  # default for 2-away

        sub_result = await EscalateGdcoTickets().run(
            EscalateGdcoTicketsInput(
                incident_id=tsg_input.incident_id,
                target_severity=target_sev,
                node_id=node_id,
                fault_description=fault_desc,
            )
        )
        return {
            "node_id": node_id,
            "action": "gdco_escalated",
            "outcome": f"GDCO ticket {sub_result.gdco_ticket_id} "
                       f"— {sub_result.escalation_result}",
        }

    async def _handle_ready_but_offline(
        self,
        tsg_input: Csm2FailuresFromQuorumLossInput,
        node: dict,
    ) -> dict:
        """Node is Ready in fabric but roles not starting.

        Wait ~45 min, then escalate to XSSE FTE.
        """
        node_id = node["node_id"]
        self.escalation_needed = True
        print(f"  Node {node_id}: Ready but CSM roles not starting")
        print("  → Wait ~45 min, then escalate to XSSE FTE")
        await self._annotate_incident(
            tsg_input,
            f"Node {node_id}: fabric state=Ready but CSM roles not starting. "
            f"Waiting ~45 min for roles to initialize. "
            f"If still offline, escalate to XSSE FTE on-call.",
        )
        return {
            "node_id": node_id,
            "action": "waiting_for_roles",
            "outcome": "Node Ready but roles not starting — "
                       "awaiting ~45 min then escalate",
        }

    async def _annotate_incident(
        self,
        tsg_input: Csm2FailuresFromQuorumLossInput,
        text: str,
    ) -> None:
        """Add a description comment to the ICM incident."""
        incident = await icm.get_incident(
            int(tsg_input.incident_id), should_get_description=False
        )
        await incident.add_description(text)
        print(f"  ICM {tsg_input.incident_id}: added note")

    # ── Step 5 — Post-mitigation ─────────────────────────────

    async def _step_5_post_mitigation(
        self, tsg_input: Csm2FailuresFromQuorumLossInput
    ) -> None:
        """Post-mitigation monitoring and follow-up.

        - Monitor self-mitigates after 120 min of healthy status.
        - Continue driving recovery even if ICM self-mitigates.
        - Public: XSSE DRI + Ops own follow-up.
        - AGC: XSSE team members must be alerted.

        AUTOMATABLE: Partially (ICM annotation is automatable,
        ongoing monitoring is human)
        """
        summary_lines = ["CSM Quorum Loss triage summary:"]
        summary_lines.append(
            f"  Tenant: {tsg_input.tenant_name} "
            f"({tsg_input.cloud_environment})"
        )
        summary_lines.append(
            f"  Offline CSMs: {len(self.offline_csms)}"
        )
        summary_lines.append(
            f"  Deployment active: {self.deployment_active}"
        )
        for r in self.recovery_results:
            summary_lines.append(
                f"  Node {r['node_id']}: {r['action']} → {r['outcome']}"
            )

        summary = "\n".join(summary_lines)
        print(summary)

        # Annotate ICM with triage summary
        await self._annotate_incident(tsg_input, summary)

        # TODO: Open Question — self-mitigation monitor metric path in Geneva
        print("\nPost-mitigation:")
        print("  - Monitor self-mitigates after 120 min of healthy status")
        print("  - Continue driving recovery of remaining offline CSMs")
        if tsg_input.cloud_environment != "Public":
            print("  - AGC: Alert XSSE team members")
