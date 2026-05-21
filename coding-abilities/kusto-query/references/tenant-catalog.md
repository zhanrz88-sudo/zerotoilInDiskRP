# Storage tenant catalog KQL patterns

These examples are **sanitized templates** for looking up tenant metadata, regions, and capacity.

Verified cluster/database (schema checked via `getschema` on 2026-03-05):

- Cluster: `https://xstore.kusto.windows.net`
- Database: `xstore`

Schema highlights (subset)

- `GetTenantCatalogLatest()` (function)
	- `Tenant: string`, `GeoRegion: string`, `DataCenter: string`
	- `Type: string` (e.g. `Storage`, `StorageFast`, `XStoreServiceFabric`)
	- `NumOfTS: int`, `NumOfFE: int`, `NumOfEn: int`
	- `IsReadyForCustomer: bool`, `IsDecomed: bool`, `Category: string`
	- `ClusterName: string`, `Environment: string`, `HardwareSetup: string`
- `TenantCatalogSnapshot` (table)
	- `Name: string`, `GeoRegion: string`, `DataCenter: string`
	- `Type: string`, `IsReadyForCustomer: string`, `IsDecomed: string`, `InDecom: string`, `InBuildOut: string`
	- `Category: string`, `ArmRegionName: string`(derived)
	- `NumOfTS: int`, `NumOfFE: int`, `NumOfEn: int`

## Example: Look up active tenants with node counts (function)

```kusto
cluster('xstore.kusto.windows.net').database('xstore').GetTenantCatalogLatest()
| where IsReadyForCustomer == true and IsDecomed == false
| project Tenant, GeoRegion, DataCenter, Type, NumOfTS, NumOfFE, NumOfEn, Category
| take <N>
```

Sample result (queried 2026-03-05, `take 3`):

| Tenant | GeoRegion | DataCenter | Type | NumOfTS | NumOfFE | NumOfEn | Category |
|---|---|---|---|---|---|---|---|
| Bleu-CYN20PrdStr01B | bleuc | CYN20 | Storage | 111 | 111 | 100 | Public |
| Bleu-CYN20PrdStr02A | bleuc | CYN20 | Storage | 111 | 111 | 100 | Public |
| Bleu-LAC20PrdStr01A | bleus | LAC20 | Storage | 111 | 111 | 100 | Public |

Inspired by:
- jupyter-templates/Xstore/Stream/AutoAnalysis/Capacity-CanEcSpeedUp.ipynb
- jupyter-templates/Xstore/Stream/HotLRC144/HotLRC144Report.ipynb

## Example: Active tenants from snapshot table (regional SRP / location service)

```kusto
cluster('xstore.kusto.windows.net').database('xstore').TenantCatalogSnapshot
| where IsReadyForCustomer == "true"
    and IsDecomed == "false"
    and InDecom == "false"
    and Category <> "PreProd"
    and InBuildOut == "false"
| project Name, Type, GeoRegion, DataCenter, NumOfTS, NumOfFE, NumOfEn
| take <N>
```

Sample result (queried 2026-03-05, `take 3`):

| Name | Type | GeoRegion | DataCenter | NumOfTS | NumOfFE | NumOfEn |
|---|---|---|---|---|---|---|
| MS-AKL02PrdStf01A | StorageFast | newzealandn | AKL02 | 51 | 51 | 50 |
| MS-AKL02PrdStf01C | StorageFast | newzealandn | AKL02 | 51 | 51 | 50 |
| MS-AKL02PrdStf02A | StorageFast | newzealandn | AKL02 | 109 | 109 | 100 |

Inspired by:
- jupyter-templates/Xstore/Location Service/Availability.ipynb

## Example: Look up EN count for a specific tenant

```kusto
cluster('xstore.kusto.windows.net').database('xstore').GetTenantCatalogLatest()
| where Tenant =~ '<tenant_name>'
| project Tenant, NumOfEn, NumOfEnZRSV, NumOfTS, NumOfFE, GeoRegion, DataCenter
```

Inspired by:
- jupyter-templates/Xstore/Stream/AutoAnalysis/Capacity-CanEcSpeedUp.ipynb

## Example: Get partition trace for a tenant (xlivesite)

Cluster: `https://xlivesite.kusto.windows.net` / Database: `xlivesite`

```kusto
let start_time = datetime(<fromTime>);
let end_time = datetime(<toTime>);

GetPartitionTraceEx(start_time, end_time, '<tenant_name>')
| where Partition == '<partition>' or ParentPartition1 == '<partition>' or ParentPartition2 == '<partition>'
| project PreciseTimeStamp, Partition, TableServer, LowKeyAccount, LowKeyContainer, LowKeyBlob, HighKeyAccount, HighKeyContainer, HighKeyBlob, Reason, LBType, DowntimeSec
| order by PreciseTimeStamp asc
| take <N>
```

Inspired by:
- jupyter-templates/Xstore/XTable/TSHighLatencyAnalysis.ipynb
