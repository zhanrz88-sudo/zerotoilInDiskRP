# Shared References — XInvestigator Process Crash TSG Family

Shared constants, contacts, and endpoints used across all TSGs in this folder.

## DGrep Configuration

| Setting | Value |
|---|---|
| Endpoint | `Diagnostics PROD` |
| Namespace | `XHealth` |
| Event | `XLivesiteLog` |
| Default Server Query | `where it.Any("Unhandled exception:")` |

## Deployment Pipelines

| Service | Build Pipeline | Definition ID |
|---|---|---|
| **XD** | [Definition 396535](https://msazure.visualstudio.com/One/_build?definitionId=396535) | 396535 |
| **AutoTsg** | [Definition 392091](https://msazure.visualstudio.com/One/_build?definitionId=392091) | 392091 |
| **AutoAnalysis** | [Definition 395813](https://msazure.visualstudio.com/One/_build?definitionId=395813) | 395813 |
| **XlivesiteCollector** | [Definition 396539](https://msazure.visualstudio.com/One/_build?definitionId=396539) | 396539 |
| **XPortal DataProvider** | [Definition 396537](https://msazure.visualstudio.com/One/_build?definitionId=396537) | 396537 |
| **XJPL Trigger** | [Definition 396381](https://msazure.visualstudio.com/One/_build?definitionId=396381) | 396381 |
| **XPortal** | [Definition 396578](https://msazure.visualstudio.com/One/_build?definitionId=396578) | 396578 |
| **ACIS Extension** | [Definition 399283](https://dev.azure.com/msazure/One/_build?definitionId=399283&_a=summary) | 399283 |

## Smoke Test Settings (XLivesiteDC Configuration)

| Test Name | Default | Critical |
|---|---|---|
| `RunXdsAccessTest` | `true` | No |
| `RunXlsAccessTest` | `true` | No |
| `RunRsrpAccessTest` | `false` | No |
| `RunIcmUpdateIncidentTest` | `true` | No |
| `RunMdsAccessTest` | `false` | No |
| `RunMdmAccessTest` | `true` | No |
| `RunHealthServiceAccessTest` | `false` | No |
| `RunOnCallClientTest` | `true` | No |
| `RunXLivesiteDCLoadTest` | `true` | No |
| `RunKustoAccessProductionTest` | `true` | No |
| `RunKustoAccessNationalCloudTest` | `false` | No |
| `RunStorageAccessTest` | `true` | No |
| `RunServiceBusTest` | `true` | **YES — NEVER SKIP** |

## Portals

| Portal | URL |
|---|---|
| ICM Portal | [portal.microsofticm.com](https://portal.microsofticm.com/) |
| DGrep Log Search | [portal.microsoftgeneva.com/logs/dgrep](https://portal.microsoftgeneva.com/logs/dgrep) |
| Azure DevOps (One) | [msazure.visualstudio.com/One](https://msazure.visualstudio.com/One/) |

## Escalation Contacts

| Team / Role | Contact | When |
|---|---|---|
| XI Service Owner | Service-specific owner (from incident routing) | Non-deployment crashes (Scenario B) |
| XInvestigator DRI | On-call via IcM routing | All process crash incidents |
| External Service Owner | Varies (e.g., Kusto team for 403 errors) | Auth/permission failures on smoke tests |

## Reference Incidents

| Incident | Description |
|---|---|
| [ICM 743516314](https://portal.microsofticm.com/imp/v5/incidents/details/743516314/summary) | AutoAnalysisWorkerRole process crash in AutoAnalysisCSESWestCentralUS |

## Reference Commits

| Commit | Description |
|---|---|
| [999f4c7f](https://msazure.visualstudio.com/One/_git/Storage-XInfrastructure/commit/999f4c7f) | Skip Kusto access smoke test (example PR for smoke test skip) |
