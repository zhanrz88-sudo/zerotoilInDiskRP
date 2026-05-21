# Shared References — Storage Node Recovery

## Kusto Endpoints

| Cloud | Cluster URI | Database |
|---|---|---|
| Public | `https://xsse.kusto.windows.net` | `xssedb` |
| USSec | `https://xsse.ussecwest.kusto.microsoft.scloud` | `xssedb` |
| USNat | `https://xsse.usnateast.kusto.eaglex.ic.gov` | `xssedb` |

## Geneva Actions

| Name | OperationId | Breadcrumb |
|---|---|---|
| Reset Node Health | `ResetNodeHealthWithSafetyChecksCrossServiceDelegated` | `Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Reset Node Health` |
| Power Node | `PowerNodeWithSafetyChecksDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Power Node With Safety Checks And Delegated Auth` |
| Put Node Into MOS | `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated` | `Xstore > Cross Service (DD/XStore) Fabric Operations with Delegated Auth > Cross Service Delegated Put Node Into MOS` |
| Request Repair (Reboot, ReimageOS, Repave, OFR) | `RequestRepairActionFromMRDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Request Repair With Delegated Auth` |
| Send Nodes to OFR with MR Override | `RequestOFRFromMRWithOverride` | `Xstore > Sustainability Operations With Delegated Auth - Safe` |

## JIT Access Requirements

| Resource Type | Instance | Access Level |
|---|---|---|
| FFE | `<ClusterId>` | PlatformAdministrator |
| XDS | `<TenantName>` | Storage-PlatformServiceOperator |
| RDM | `<PfClusterName>` | RdmAdministrator |

Portal: [aka.ms/JIT](https://aka.ms/JIT)

## Tools

| Tool | URL / Install |
|---|---|
| FcShell | [aka.ms/fcshell](https://aka.ms/fcshell) |
| DCM Explorer | [aka.ms/dcmexplorer](https://aka.ms/dcmexplorer) |
| Geneva Actions | [portal.microsoftgeneva.com/actions](https://portal.microsoftgeneva.com/actions) |

## Escalation Contacts

| Team | Contact | When |
|---|---|---|
| XSSE DRI (Public) | [IcM On-Call](https://portal.microsofticm.com/imp/v3/oncall/current?serviceId=10050&teamIds=42293) | HI recovery failures in Public |
| XSSE (AGC) | `xsse-tented@microsoft.com` | All AGC escalations |
| MR Team | `xstoremr@microsoft.com` | Geneva Action failures |
| DD Hardware Support | `xdirecthwsupport@microsoft.com` | Hardware SOPs |
| Titan Agents Team | (via IcM) | PfAgent issues (FC 8) |
