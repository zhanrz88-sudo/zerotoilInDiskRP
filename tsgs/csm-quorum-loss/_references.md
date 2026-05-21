# Shared References — CSM Quorum Loss TSG Family

Shared constants, contacts, and endpoints used across all TSGs in this folder.

## Kusto Endpoints

| Cloud | Cluster URI | Database |
|---|---|---|
| Public | `https://xsse.kusto.windows.net` | `xssedb` |
| USSec | `https://xsse.ussecwest.kusto.microsoft.scloud` | `xssedb` |
| USNat | `https://xsse.usnateast.kusto.eaglex.ic.gov` | `xssedb` |

## Geneva Actions (Allowed for Non-XSSE DRIs)

| # | Name | OperationId | Breadcrumb |
|---|---|---|---|
| 1 | Reset Node Health | `ResetNodeHealthWithSafetyChecksCrossServiceDelegated` | `Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Reset Node Health` |
| 2 | Power Node | `PowerNodeWithSafetyChecksDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Power Node With Safety Checks And Delegated Auth` |
| 3 | Put Node Into MOS | `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated` | `Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Put Node Into MOS` |
| 4 | GDCO Change Severity | `GDCOChangeSeverity` | `Sustainability Operations - Safe` |

## JIT Access Requirements

| Resource Type | Instance | Access Level |
|---|---|---|
| FFE | `<ClusterId>` | PlatformAdministrator |
| XDS | `<TenantName>` | Storage-PlatformServiceOperator |
| RDM | `<PfClusterName>` | RdmAdministrator |

Portal: [aka.ms/JIT](https://aka.ms/JIT)

## Dashboards

| Dashboard | URL |
|---|---|
| CSM Quorum Health | [Geneva](https://portal.microsoftgeneva.com/s/6CAF71FC) |
| DU Tracking + Nodes | [Jarvis](https://jarvis-west.dc.ad.msft.net/dashboard/XStore/xSSE/DU%2520Tracking%2520%252B%2520Nodes) |
| Ring Health (vNext) | [Jarvis](https://jarvis-west.dc.ad.msft.net/dashboard/XStore/vNext/RingHealth) |

## Portals

| Portal | URL |
|---|---|
| xPortal | [aka.ms/xportal](https://aka.ms/xportal) |
| Geneva Actions | [portal.microsoftgeneva.com/actions](https://portal.microsoftgeneva.com/actions) |
| GDCO App | [gdcoapp.trafficmanager.net](https://gdcoapp.trafficmanager.net) |

## Escalation Contacts

| Team | Contact | When |
|---|---|---|
| XSSE DRI (Public) | [IcM On-Call](https://portal.microsofticm.com/imp/v3/oncall/current?serviceId=10050&teamIds=42293) | HI recovery failures |
| XSSE (AGC) | `xsse-tented@microsoft.com` | All AGC escalations |
| xcsmdev | `xcsmdev@microsoft.com` | CSM software crashes |
| XDeployment | `xdep@microsoft.com` | Block upgrades |
| MR Team | `xstoremr@microsoft.com` | Geneva Action failures |
| DD Hardware Support | `xdirecthwsupport@microsoft.com` | Hardware SOPs |
| Sparing | Juil Sohng, Shanqin Liu, Colin Cury | DC parts availability |

## Related TSGs (External)

| TSG | Link | Called From |
|---|---|---|
| Storage Node Recovery (parent — JIT + Precautions) | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/Storage%20Node%20Recovery.md&_a=preview) | Step 4 (HI nodes) |
| Storage Node Recovery — FC 8 | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%208%20-%20Node%20Recovery.md&_a=preview) | Step 4 (HI nodes with FC 8) |
| Escalate GDCO Tickets | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Escalate%20GDCO%20Tickets.md&_a=preview) | Step 4 (OFR nodes) — sub-TSG in this folder |
| Data Unavailability (DU) | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Data%20Unavailability%20Alert%20%28DU%29.md&_a=preview) | Severity Guide (quorum loss) |
| RSL Ring Recovery (vNext) | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Stream_Layer/tsgs/CSM-vNext/RSL/Ring-recovery.md&_a=preview) | Related — vNext CSM |
| Deadlocked CSM | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Stream_Layer/tsgs/CSM/DeadlockedCsm/Mitigate.md&_a=preview) | Related — software issue |
| CSM 1-Away Mitigate | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Stream_Layer/tsgs/CSM/CloseToQuorumLoss/Mitigate.md&_a=preview) | Related — severity escalation |
| Common Scenarios | [ADO](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Common%20Scenarios.md&_a=preview) | Related — general reference |
