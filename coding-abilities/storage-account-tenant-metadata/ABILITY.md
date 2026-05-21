---
name: Storage Account & Tenant Metadata
description: Look up storage account metadata, resolve the home storage tenant, and find the geo-pair tenant for geo-redundant accounts.
---

# Coding Ability: storage-account-tenant-metadata

## Description

Resolves the relationship between a storage account name, its home storage tenant (stamp), and the geo-pair tenant using the `xstore` metadata APIs. This is essential for any TSG that needs to search XDS logs for a customer account, because XDS logs live on the **storage tenant**, not on the SRP (control-plane) tenant.

- **Read-only.** All calls are metadata lookups; no mutations.
- Requires the `xstore` package (available in XPortal Jupyter / XScript runtime).
- Account names are globally unique within an environment (e.g., Production, Mooncake, Fairfax, USNat, USSec).

Key concepts

- **Storage account** (`Account`): A customer-facing storage account (e.g., `ppthdprod`). Has metadata including `TenantName`, `AccountType`, `GeoPairName`, `GeoRegion`, `State`, etc.
- **Storage tenant** (a.k.a. stamp): The physical cluster that hosts the account's data (e.g., `MS-MEL23PrdStr11D`). XDS logs, role instances, and infrastructure diagnostics are scoped to this tenant. Names typically start with `MS-` or follow a pattern like `<region><id>prdstr<etc>`.
- **SRP tenant**: A control-plane tenant whose name starts with `RSRP` (e.g., `RSRPAustraliaEast`). These are Regional Storage Resource Provider tenants that control account-to-stamp allocation. DGrep events like `ServiceBackgroundActivityEvent` and `AccountFailoverEvent` are scoped to SRP tenants.
- **Geo-pair tenant**: For geo-redundant accounts (`StandardGRS`, `StandardRAGRS`), the secondary storage tenant in the paired region. Accessible via `tenant_entity.GeoPairName` or `account_entity.GeoPairName`.
- **When to use which tenant**:
  - **DGrep queries** (e.g., `dgrep.query(scope_conditions={"Tenant": ...})`) use the **SRP tenant** (e.g., `RSRPAustraliaEast`) or the **storage tenant**, depending on the event namespace.
  - **XDS log searches** (`xds.search_log(tenant_name, ...)`) always use the **storage tenant** (e.g., `MS-MEL23PrdStr11D`).
  - **XDS API calls** (`xds_client` `ApiClient.connect_tenant(...)`) always use the **storage tenant**.

## Remarks

> **NEVER substitute the SRP/RSRP tenant for a storage tenant.**
> SRP tenants (e.g. `RSRPAustraliaEast`, `RSRPPublicPreprodEastUS2`) are
> control-plane stamps that allocate, fail over, and migrate accounts.
> They do **not** host XDS role instances or XDS logs. Calling
> `xds.search_log("RSRP...", ...)` returns HTTP 500 / `EndpointNotFoundException`
> because there is no XDS SOAP endpoint at that name. If `get_account()` fails
> and you cannot resolve the real storage tenant, leave `storage_tenant`
> empty and let the TSG follow its existing 'no storage tenant' branch
> (typically a default escalation). Do NOT invent a stand-in.

### Backend vs local `xstore` versions (important deployment note)

There are two `get_account` implementations in the wild:

- **Local `zero-toil/.venv` (newer):** Tries the XDS account metadata
  service first, then falls back to **Kusto** via the XPortal REST API
  (`/api/v1/AccountMetadata/GetAccountMetadataFromKusto`). This covers
  many accounts not exposed by XDS, including most RSRP PreProd accounts.
- **XJupyterLite backend image (older):** Only consults the XDS
  account metadata service. Raises `StorageAccountNotFoundError` for
  accounts that exist in Kusto but not in XDS — common for
  `RSRPPublicPreprod*` test accounts.

**Always run `inspect.getsource(get_account)` on the target environment
before assuming behaviour parity.** A backend introspection job (see
`run-zerotoil-job-in-backend` skill) is the fastest way to confirm.
The proper fix for the backend gap is to upgrade the `xstore` image,
not to work around it in TSG code.

### `get_account()` -- look up storage account metadata

```python
from xstore import get_account

async def get_account(
    account_name: str,
    environment: Optional[str] = None,   # "Production" | "Mooncake" | "Fairfax" | "USNat" | "USSec"
) -> Account
```

Source: `zero-toil/.venv/Lib/site-packages/xstore/common/account.py`

**`Account`** commonly used fields:

| Field | Type | Description |
|---|---|---|
| `TenantName` | `str` | Home storage tenant (stamp) name, e.g. `MS-MEL23PrdStr11D` |
| `AccountType` | `Any` | Account redundancy type, e.g. `StandardGRS`, `StandardLRS`, `StandardZRS` |
| `GeoRegion` | `str` | Geographic region, e.g. `Australia East` |
| `ArmRegionName` | `str` | ARM region, e.g. `australiaeast` |
| `GeoPairName` | `str` | Geo-pair tenant name (for GRS accounts), e.g. `MS-SYD24PrdStr02A` |
| `GeoReplicationEnabled` | `bool` | Whether geo-replication is active |
| `State` | `str` | Account state, e.g. `State_Active`, `State_Deleted` |
| `VersionedAccountName` | `str` | Versioned account name, e.g. `ppthdprod.0` |
| `Subscription` | `str` | Azure subscription ID |
| `AccountFailoverStage` | `str` | Current failover stage if in progress |
| `LastFailoverType` | `str` | e.g. `Soft`, `Hard` |
| `IsPremium` | `bool` | Whether this is a premium account |
| `CreationTime` | `datetime` | Account creation time |

### `get_tenant()` -- look up storage tenant metadata

```python
from xstore import get_tenant

async def get_tenant(
    tenant_name: str,
) -> Tenant
```

Source: `zero-toil/.venv/Lib/site-packages/xstore/common/tenant.py`

**`Tenant`** commonly used fields:

| Field | Type | Description |
|---|---|---|
| `Name` | `str` | Tenant name, e.g. `MS-MEL23PrdStr11D` |
| `GeoPairName` | `str` | Geo-pair tenant name, e.g. `MS-SYD24PrdStr02A` |
| `GeoRegion` | `str` | Geographic region |
| `ArmRegionName` | `str` | ARM region name |
| `RsrpName` | `str` | Associated RSRP tenant name, e.g. `RSRPAustraliaEast` |
| `Environment` | `str` | e.g. `Production`, `Mooncake` |
| `Category` | `str` | Tenant category |
| `Type` | `str` | e.g. `StorageProvisioned`, `Storage` |
| `State` | `str` | Tenant state |
| `XdsEndpoint` | `str` | XDS endpoint URL |
| `ClusterName` | `str` | Cluster name |
| `IsLimitless` | `bool` | Whether this is a limitless tenant |
| `ZrsSetup` | `Any` | ZRS configuration (e.g., `ZRSVirtual`) |
| `LimitlessClusterGroup` | `Any` | Limitless cluster group info |

Helper methods on `Tenant`:
- `await tenant_entity.get_available_xds_endpoint()` -- resolves XDS endpoint (handles ZRS virtual tenants)
- `await tenant_entity.get_role_instances()` -- list role instances on the tenant
- `await tenant_entity.get_physical_tenants()` -- for ZRS virtual tenants, get the underlying physical tenants

## Sample Python code

```python
from xstore import get_account, get_tenant

# 1. Look up account metadata
account_entity = await get_account("<account_name>")
print(f"Account: {account_entity.VersionedAccountName}")
print(f"Home tenant (stamp): {account_entity.TenantName}")
print(f"Account type: {account_entity.AccountType}")
print(f"Geo region: {account_entity.GeoRegion}")
print(f"Geo pair: {account_entity.GeoPairName}")
print(f"State: {account_entity.State}")

# 2. Get the home storage tenant entity
home_tenant = await get_tenant(account_entity.TenantName)
print(f"Home tenant XDS endpoint: {home_tenant.XdsEndpoint}")
print(f"Home tenant RSRP: {home_tenant.RsrpName}")

# 3. Get the geo-pair tenant (for GRS accounts)
if account_entity.GeoPairName:
    geo_pair_tenant = await get_tenant(account_entity.GeoPairName)
    print(f"Geo-pair tenant: {geo_pair_tenant.Name}")
    print(f"Geo-pair region: {geo_pair_tenant.GeoRegion}")

# 4. Use the storage tenant for XDS log searches
from xstore import xds

result = await xds.search_log(
    account_entity.TenantName,      # Storage tenant, NOT SRP tenant
    from_time,
    to_time,
    ['xacserver'],
    log_type='Verbose',
    search_string="<account_name>",
)
```
