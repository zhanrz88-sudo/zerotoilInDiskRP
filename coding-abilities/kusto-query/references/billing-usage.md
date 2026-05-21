# Billing / usage / transactions KQL patterns

These examples are **sanitized templates**.

Verified cluster/database (schema checked via `getschema` on 2026-03-05):

- Cluster: `https://xdataplane.kusto.windows.net`
- Database: `XMeter`

Schema highlights (subset)

- `XStoreAccountRealtimeTransaction`
  - `TIMESTAMP: datetime`, `Account: string`, `RequestType: string`
  - `TransactionCount: long`, `TotalSuccessCount: long`
  - `ServerTimeoutError: long`, `ClientTimeoutError: long`, `ThrottlingError: long`

- Replace placeholders like `<accountPrefix>`, `<fromTime>`, `<toTime>`, `<N>`.
- Prefer a narrow time range when iterating.

## Example: Transaction counts and failure rate (per minute)

```kusto
let start_time = datetime(<fromTime>);
let end_time = datetime(<toTime>);

XStoreAccountRealtimeTransaction
| where TIMESTAMP between (start_time .. end_time)
| where Account startswith '<accountPrefix>'
| where RequestType contains '<requestTypeHint>'
| summarize
    TransactionCount = sum(TransactionCount),
    FailureCount = sum(TransactionCount - TotalSuccessCount),
    ServerTimeoutCount = sum(ServerTimeoutError),
    ClientTimeoutCount = sum(ClientTimeoutError),
    ThrottlingCount = sum(ThrottlingError)
  by bin(TIMESTAMP, 1m)
| extend FailureRate = todouble(FailureCount) / todouble(TransactionCount)
| order by TIMESTAMP asc
| take <N>
```

Sample result (queried 2026-03-05, aggregated across all accounts, `RequestType contains 'Blob'`, `bin(TIMESTAMP, 5m)`, `take 3`):

| TIMESTAMP | TransactionCount | FailureCount | ServerTimeoutCount | ClientTimeoutCount | ThrottlingCount | FailureRate |
|---|---|---|---|---|---|---|
| 2026-03-05T03:10:00Z | 82,396,128,435 | 3,279,990,594 | 384,597 | 62,424 | 98,060,266 | 0.0398 |
| 2026-03-05T03:15:00Z | 76,421,241,334 | 3,016,829,267 | 377,691 | 51,617 | 81,706,207 | 0.0395 |

Inspired by:
- jupyter-templates/Xstore/XInvestigator/AccountAvailibilityDiagnostic.ipynb
