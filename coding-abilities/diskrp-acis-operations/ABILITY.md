# DiskRP ACIS Geneva Action Operations

## Purpose

Invoke DiskRP Geneva Actions programmatically via `xportal.acis` for disk/snapshot read and mutating operations under the `Compute Platform Disks` ACIS extension.

## Remarks

- Extension name is `Compute Platform Disks` (not `Xstore`).
- The old `Xstore/RunXDiagCmdLetScript` operation is **DISABLED** (returns HTTP 500). All DiskRP operations have moved to `Compute Platform Disks`.
- **Endpoint naming varies by auth path:**
  - dSTS (SAW / XJupyterLite browser): use `endpoint='Prod'`
  - Backend worker (AKS cert): use `endpoint='Production'`
  - When in doubt, try `Prod` first — if it fails with "endpoint not found", try `Production`.
- Parameters are **positional** — order matters for `acis.execute()` / `acis.submit()`.
- `acis.execute()` is synchronous (submits and waits). Works for read-only ops from backend worker (cert auth) or from SAW (dSTS).
- `acis.submit()` + `acis.get_result()` is async. **Requires dSTS auth on SAW** — blocked for corp AAD accounts (`HttpForbiddenError: Microsoft corp account is not supported`).
- `acis.get_result()` signature: `acis.get_result(extension_name, response_id, wait_for_completion=True)` — first arg is extension name, not just the action ID.
- Backend worker identity (`StoragePlatformServiceViewer`) has **read-only claims only**. It can execute `GetDisk`, `GetSnapshot`, etc. but **cannot** execute mutating ops like `RemoveIncrementalSnapshotFamilyOnDisk`.
- JIT (`DiskRP-CustomerServiceOperator`) elevates the **user's AAD identity**, not the backend worker cert. No delegation/impersonation mechanism exists.
- Mutating operations must be run from **SAW with dSTS auth** or from the **Geneva Actions portal UI**.
- **`resultMessage` is NOT always JSON.** When a ACIS operation returns an error (e.g., disk NotFound), `resultMessage` contains a raw error string (e.g., `[Response] StatusCode: NotFound, Headers: ...`). Always wrap `json.loads(r['resultMessage'])` in try/except or check `msg.startswith('{')` before parsing. Unhandled JSONDecodeError causes `NotebookException` on the backend.

## Validated Operations

All validated via real `acis.execute()` calls on 2026-05-19/20.

| OperationId | Purpose | Mutating? | Endpoint (dSTS) | Endpoint (AKS) | Params |
|---|---|---|---|---|---|
| `GetDisk` | Get disk metadata including internal XStore fields | No | `Prod` | `Prod` | `[subscriptionId, region, resourceGroup, diskName]` |
| `GetSnapshot` | Get snapshot metadata including storage account, blob URL, ISF | No | `Prod` | `Prod` | `[subscriptionId, region, resourceGroup, snapshotName]` |
| `GetStorageAccount` | Get storage account metadata, disks, and snapshots | No | `Prod` | `Prod` | `[subscriptionId, region, storageAccountName, apiVersion]` |
| `GetSubscriptionSettings` | Get DiskRP subscription settings | No | `Prod` | `Prod` | `[subscriptionId, region, apiVersion]` — region is **required** (ARM-cased) |
| `ListDisks` | List disks in a resource group | No | — | — | Not yet validated |
| `ListSnapshots` | List snapshots in a resource group | No | — | — | Not yet validated |
| `GetDiskEncryptionSet` | Get DES metadata | No | — | — | Not yet validated |
| `RemoveIncrementalSnapshotFamilyOnDisk` | Break ISF association on a disk | **Yes** | `Prod` | `Production` | `[subscriptionId, region, resourceGroup, diskName, skipValidation, clearBilling, apiVersion]` |

## Prerequisite: Kusto lookup

Before calling GetDisk/GetSnapshot/GetSubscriptionSettings, always query Kusto to get the correct **region** — do not guess. Region must be ARM-cased (e.g. `EastUS2EUAP`, not `eastus2euap`).

### Kusto Clusters

| Cluster | Database | Auth Resource | Use For |
|---|---|---|---|
| `disks.kusto.windows.net` | `disks` | `https://disks.kusto.windows.net` | `DiskManagerApiQoSEvent` — region lookup by subscriptionId, disk QoS events |
| `disksbi.kusto.windows.net` | `DisksBI` | `https://disksbi.kusto.windows.net` | `ManagedDiskBIEntity` — storage account metadata, PoolManagerId → region |

**`disksbi` throttles aggressively.** When throttled, fall back to `disks.kusto.windows.net` for region lookups:

```bash
# Region lookup via disks cluster (fallback when disksbi is throttled)
az rest --method post --url "https://disks.kusto.windows.net/v1/rest/query" ^
  --body @query.json --resource "https://disks.kusto.windows.net"

# query.json:
# {"db":"disks","csl":"DiskManagerApiQoSEvent | where subscriptionId == '<sub>' | project RPTenant, region | take 1"}
```

```bash
# Storage account lookup via disksbi cluster
az rest --method post --url "https://disksbi.kusto.windows.net/v1/rest/query" ^
  --body @query.json --resource "https://disksbi.kusto.windows.net"

# query.json:
# {"db":"DisksBI","csl":"StorageAccount | where Name == '<account>' | project SubscriptionId, PoolManagerId | take 1"}
# Region from PoolManagerId: fabric:/DiskRP-westus3_4/... → WestUS3
```

**Note:** The backend worker (Test environment) cannot query the Disks Kusto cluster (fails with "Invalid cloud specified" for cloud=Test). Use `az rest` locally instead.

## Sample Code

### Read-only: GetDisk (works from backend or SAW)

```python
from xportal import acis
import json

result = await acis.execute(
    'Compute Platform Disks',
    'GetDisk',
    ['<subscriptionId>', '<region>', '<resourceGroup>', '<diskName>'],
    'Prod',
)
parsed = json.loads(result['resultMessage']) if isinstance(result, dict) else result
print(json.dumps(parsed, indent=2))
```

### Read-only: GetSnapshot (works from backend or SAW)

```python
result = await acis.execute(
    'Compute Platform Disks',
    'GetSnapshot',
    ['<subscriptionId>', '<region>', '<resourceGroup>', '<snapshotName>'],
    'Prod',
)
print(result)
```

### Read-only: GetStorageAccount (works from backend or SAW)

```python
from xportal import acis
import json

result = await acis.execute(
    'Compute Platform Disks',
    'GetStorageAccount',
    ['<subscriptionId>', '<region>', '<storageAccountName>', ''],  # apiVersion can be empty
    endpoint='Prod',
)
parsed = json.loads(result['resultMessage']) if isinstance(result, dict) else result
print(json.dumps(parsed, indent=2))
# Returns: name, pseudoSubscriptionId, accountType, relativeAccountUri, poolManagerId,
#          disks[] (list of disks on this account), snapshots[] (list of snapshots with full metadata)
```

**GetStorageAccount returns:** Storage account metadata plus **all disks and snapshots** on that account with full properties including `incrementalSnapshotFamilyId`, `blobUrl`, `storageAccountName`, `diskState`, etc.

**Kusto lookup for storage accounts** — use `disksbi.kusto.windows.net` / `DisksBI` database:
```python
# az rest --method post --url "https://disksbi.kusto.windows.net/v1/rest/query" \
#   --body @query.json --resource "https://help.kusto.windows.net" \
#   --headers "Content-Type=application/json"
# query.json: {"db":"DisksBI","csl":"StorageAccount | where Name =='md-xxxx' | take 1"}
# Key fields: Name, SubscriptionId, PseudoSubscriptionId, AccountType, PoolManagerId, AccountUri, State
```

**Geneva Actions portal URL for GetStorageAccount:**
```
https://portal.microsoftgeneva.com/?page=actions&extension=Compute%20Platform%20Disks&group=Storage%20Account%20Operations&operationId=GetStorageAccount&endpoint=Prod&wellknownsubscriptionid=<sub>&smeregionarmnameparameter=<region>&smestorageaccountnameparameter=<accountName>&smeapiversionparameter=
```

### Mutating: RemoveIncrementalSnapshotFamilyOnDisk (SAW only)

```python
from xportal import acis
import json

ext = 'Compute Platform Disks'
op = 'RemoveIncrementalSnapshotFamilyOnDisk'
params = [
    '<subscriptionId>',
    '<region>',
    '<resourceGroup>',
    '<diskName>',
    'false',        # skipValidation
    'false',        # clearBilling
    '',             # apiVersion (leave empty for default)
]

# Submit (requires dSTS on SAW — fails with corp AAD)
response = await acis.submit(ext, op, params, endpoint='Prod')
print('Submitted:', response)

# Poll for result (first arg is extension_name, not action_id!)
aid = response.get('id') or response.get('executionId')
result = await acis.get_result(ext, aid, wait_for_completion=True)
print(json.dumps(result, indent=2) if isinstance(result, dict) else result)
```

### Compact version for XJupyterLite on SAW

```python
from xportal import acis
import json
ext = 'Compute Platform Disks'
op = 'RemoveIncrementalSnapshotFamilyOnDisk'
p = ['<sub>','<region>','<rg>','<disk>','false','false','']
r = await acis.submit(ext, op, p, endpoint='Prod')
print(r)
aid = r.get('id') or r.get('executionId')
res = await acis.get_result(ext, aid, wait_for_completion=True)
print(res)
```

## XJupyterLite on SAW

- **URL:** `https://xportal.trafficmanager.net/xjupyterlite/lab/index.html`
- This is the dSTS endpoint — only works on SAW
- Corp AAD endpoint: `https://xportal-aad.trafficmanager.net/xjupyterlite/lab/index.html` (cannot do mutating ops)

### ISF Break on SAW — Step-by-Step

**Prerequisites:**
1. Log into **SAW** (Secure Admin Workstation)
2. Activate **JIT**: `DiskRP-CustomerServiceOperator` role (grants mutating ACIS claims)
3. Open XJupyterLite on SAW: `https://xportal.trafficmanager.net/xjupyterlite/lab/index.html` (dSTS auth)

**Step 1: Identify the disk** — get subscriptionId, region, resourceGroup, diskName from the ICM incident or Kusto:
```python
# Kusto query (run locally or on SAW):
# cluster: disks.kusto.windows.net / database: Disks
# DiskManagerApiQoSEvent | where resourceName == '<diskName>' | project subscriptionId, region, resourceGroupName | take 1
```

**Step 2: Verify the disk** — run GetDisk to confirm ISF ID and current state:
```python
from xportal import acis
import json

result = await acis.execute(
    'Compute Platform Disks', 'GetDisk',
    ['<subscriptionId>', '<region>', '<resourceGroup>', '<diskName>'],
    endpoint='Prod',
)
parsed = json.loads(result['resultMessage'])
print(f"ISF ID: {parsed['properties']['incrementalSnapshotFamilyId']}")
print(f"State:  {parsed['properties']['diskState']}")
```

**Step 3: Break ISF** — submit the mutating operation:
```python
ext = 'Compute Platform Disks'
op = 'RemoveIncrementalSnapshotFamilyOnDisk'
params = ['<subscriptionId>', '<region>', '<resourceGroup>', '<diskName>', 'false', 'false', '']

response = await acis.submit(ext, op, params, endpoint='Prod')
print('Submitted:', response)

aid = response.get('id') or response.get('executionId')
result = await acis.get_result(ext, aid, wait_for_completion=True)
print(json.dumps(result, indent=2) if isinstance(result, dict) else result)
```

**Step 4: Verify ISF removed** — re-run GetDisk and confirm `incrementalSnapshotFamilyId` is now `null`.

**Alternative: Geneva Actions Portal UI**
```
https://portal.microsoftgeneva.com/?page=actions&extension=Compute%20Platform%20Disks&operationId=RemoveIncrementalSnapshotFamilyOnDisk&endpoint=Prod
```
Fill in: subscriptionId, region, resourceGroup, diskName, skipValidation=false, clearBilling=false, apiVersion=(empty)

## Geneva Actions Portal (alternative for mutating ops)

URL pattern with pre-filled params:
```
https://portal.microsoftgeneva.com/?page=actions&extension=Compute%20Platform%20Disks&operationId=RemoveIncrementalSnapshotFamilyOnDisk&endpoint=Prod&wellknownsubscriptionid=<sub>&smeregionarmnameparameter=<region>&smeresourcegroupnameparameter=<rg>&smedisknameparameter=<disk>&smeskipvalidationparameter=false&smeclearbillingparameter=false&smeapiversionparameter=
```

## Permission Model

| Identity | Claims | Can do read-only? | Can do mutating? |
|---|---|---|---|
| Backend worker cert (`StoragePlatformServiceViewer`) | 11 `*-PlatformServiceViewer` claims (see below) | ✅ Yes | ❌ No |
| User with JIT (`DiskRP-CustomerServiceOperator`) on SAW | Elevated user principal | ✅ Yes | ✅ Yes (dSTS only) |
| User corp AAD (no SAW) | Standard user | ❌ Blocked by `is_aad_auth()` | ❌ Blocked |

### Backend Worker Claims (11 total)

All are read-only `PlatformServiceViewer` claims. Verified 2026-05-20 via job `9425ccd3`.

| # | Claim |
|---|---|
| 1 | `NRP-PlatformServiceViewer` |
| 2 | `NetMon-PlatformServiceViewer` |
| 3 | `DiskRPSupport-PlatformServiceViewer` |
| 4 | `SRP-PlatformServiceViewer` |
| 5 | `svalinngenevaaction-PlatformServiceViewer` |
| 6 | `Storage-PlatformServiceViewer` |
| 7 | `AzureUsageBilling-PlatformServiceViewer` |
| 8 | `SPARTAPartner-PlatformServiceViewer` |
| 9 | `PhyNetDiagnostics-PlatformServiceViewer` |
| 10 | `Archive-PlatformServiceViewer` |
| 11 | `GenevaActionsCommon-PlatformServiceViewer` |

**Mutating ops require:** `DiskRP-CustomerServiceOperator` or `DiskRP-CustomerServiceAdministrator` (granted via JIT on SAW).

### ApproveFeatureRegistration Required Claims

This operation uses `Azure Resource Manager` extension (not `Compute Platform Disks`) and requires one of these `*-PlatformServiceOperator` or `*-PlatformServiceAdministrator` claims (verified 2026-05-21 via job `b141609c`):

| Operator Claims | Administrator Claims |
|---|---|
| `CRP-PlatformServiceOperator` | `CRP-PlatformServiceAdministrator` |
| `CloudServicesExtendedSupport-PlatformServiceOperator` | `CloudServicesExtendedSupport-PlatformServiceAdministrator` |
| `PIR-PlatformServiceOperator` | `PIR-PlatformServiceAdministrator` |
| `CDRP-PlatformServiceOperator` | `CDRP-PlatformServiceAdministrator` |
| `DiskRP-PlatformServiceOperator` | `DiskRP-PlatformServiceAdministrator` |
| `CPlatAFEC-PlatformServiceOperator` | `CPlatAFEC-PlatformServiceAdministrator` |
| | `AFECAutomation-PlatformServiceAdministrator` |
| | `AFECLionrock-PlatformServiceAdministrator` |
| | `SPARTA-PlatformServiceAdministrator` |

The backend worker has **none** of these — it only has `*-PlatformServiceViewer` claims. Feature approvals must be done on SAW with JIT.

## Backend Job Reports

| Job ID | What | Result | Date |
|---|---|---|---|
| `875e59ab-5e82-40a5-ac24-f3be0c53ee30` | Probed 25+ ACIS operations | Found 6 valid ops | 2026-05-19 |
| `82620f00-ef33-490c-a0a9-a221fd0cb1f3` | GetDisk (wrong RG) | NotFound (deleted disk) | 2026-05-19 |
| `72fb7634-a5ef-4adf-9ed3-a8f0bbf298af` | GetSnapshot success | Full snapshot metadata | 2026-05-19 |
| `70ee9e50-2a96-4166-891e-9f9029b54d4b` | GetDisk (correct RG `diskrptestypezj`) | Full disk metadata | 2026-05-20 |
| `5b5e3dc4-aa4b-4bbe-b716-527f4ea6279b` | Break ISF via backend | Failed — claims error | 2026-05-20 |
| `744119ec-ff52-4fde-b045-8ff16676dce3` | GetStorageAccount `md-0mt2tjswlrgs` | Success — full account + 3 snapshots | 2026-05-20 |
