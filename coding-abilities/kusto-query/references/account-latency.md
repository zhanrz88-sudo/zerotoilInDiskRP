# Account & latency KQL patterns (XArgus, XMeter)

These examples are **sanitized templates** for account-level performance investigation.

Verified cluster/databases (schema checked via `getschema` on 2026-03-05):

- XArgus latency: `https://xargus.centralus.kusto.windows.net` / `Production`
- Billing/transactions: `https://xdataplane.kusto.windows.net` / `XMeter`

Schema highlights (subset)

- `AccountPerfPercentiles5M` (XArgus)
	- `TimeWindow: datetime`, `Tenant: string`, `Account: string`
	- `Operation: string`, `EntityType: string`, `RequestCount: long`
	- `ServerTimeMs_Avg: real`, `ServerTimeMs_P99_0: real`
	- `FeTimeMs_P99_0: real`, `TsTimeMs_P99_0: real`
	- `TsOnlyTimeMs_P99_0: real`, `StreamTimeMs_P99_0: real`
	- `LastTS: string`, `BilledSubscription: string`

## Example: Top high-latency requests for a storage account (P99 server time)

```kusto
let _startTime = ago(<hours>h);
let _endTime = now();

cluster('xargus.centralus.kusto.windows.net').database('Production').AccountPerfPercentiles5M
| where TimeWindow >= _startTime and TimeWindow < _endTime
| where Account == '<account_name>'
| where Tenant =~ '<tenant_name>'
| top 5 by ServerTimeMs_P99_0
| project TimeWindow, Tenant, Account, Operation, EntityType, RequestCount,
    ServerTimeMs_Avg = round(ServerTimeMs_Avg, 2),
    ServerTimeMs_P99_0 = round(ServerTimeMs_P99_0, 2),
    FeTimeMs_P99_0 = round(FeTimeMs_P99_0, 2),
    TsTimeMs_P99_0 = round(TsTimeMs_P99_0, 2),
    TsOnlyTimeMs_P99_0 = round(TsOnlyTimeMs_P99_0, 2),
    StreamTimeMs_P99_0 = round(StreamTimeMs_P99_0, 2),
    LastTS, BilledSubscription
```

Sample result (queried 2026-03-05, `ServerTimeMs_P99_0 > 100`, `hours = 1`, `top 3`):

| TimeWindow | Tenant | Account | Operation | EntityType | RequestCount | ServerTimeMs_Avg | ServerTimeMs_P99_0 | TsTimeMs_P99_0 | LastTS |
|---|---|---|---|---|---|---|---|---|---|
| 2026-03-05T02:40:00Z | MS-BLZ25PrdStrz04A | prduezrbackup | GetBlob | BlockBlob | 8 | 183001.4 | 618160.57 | 58603.24 | ms-blz25prdstrz04a$ms-mnz26prdstr14a:xtableserver_in_148 |
| 2026-03-05T02:35:00Z | MS-DUB14PrdStr05C | hr3nimuostyqm | GetBlob | BlockBlob | 6 | 585780.34 | 613759.28 | 2919.98 | ms-dub14prdstr05c$xtableserver_in_164 |
| 2026-03-05T02:55:00Z | MS-BLZ25PrdStrz04A | prduezrbackup | GetBlob | BlockBlob | 6 | 336493.79 | 535941.16 | 44406.53 | ms-blz25prdstrz04a$ms-blz25prdstr04a:xtableserver_in_218 |

Inspired by:
- jupyter-templates/Xstore/XTable/TSHighLatencyAnalysis.ipynb

## Example: High-latency requests filtered by operation and entity type

```kusto
let _startTime = ago(<hours>h);
let _endTime = now();

cluster('xargus.centralus.kusto.windows.net').database('Production').AccountPerfPercentiles5M
| where TimeWindow >= _startTime and TimeWindow < _endTime
| where Account == '<account_name>'
| where Tenant =~ '<tenant_name>'
| where Operation == '<operation>'       // e.g. 'GetBlob', 'PutBlob', 'GetEntity'
| where EntityType == '<entity_type>'    // e.g. 'BlockBlob', 'PageBlob', 'Table'
| where ServerTimeMs_P99_0 > <threshold_ms>
| project TimeWindow, Operation, EntityType, RequestCount,
    ServerTimeMs_P99_0 = round(ServerTimeMs_P99_0, 2),
    TsTimeMs_P99_0 = round(TsTimeMs_P99_0, 2),
    StreamTimeMs_P99_0 = round(StreamTimeMs_P99_0, 2),
    LastTS
| order by ServerTimeMs_P99_0 desc
| take <N>
```

Inspired by:
- jupyter-templates/Xstore/XTable/TSHighLatencyAnalysis.ipynb
- jupyter-templates/Xstore/Developer/neelparikh/MAL-Latency-Analysis.ipynb
