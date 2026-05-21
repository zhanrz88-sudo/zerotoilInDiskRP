# Step 2 — Analyze error pattern

> **Parent TSG**: [xinvestigator-process-crash](../xinvestigator-process-crash.md)
> **Maps to**: `_step_2_analyze_error_pattern()` method

## Purpose

Classify the exception pattern from DGrep crash logs to determine whether the crash is caused by a smoke test failure or a different production issue. Extract key metadata for downstream mitigation routing.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `crash_logs` | `DataFrame` | From Step 1 |
| `log_count` | `int` | From Step 1 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `error_classification` | `str` | `smoke_test_failure`, `non_smoke_test_crash`, or `no_logs_found` |
| `exception_type` | `str` | Exception class name (e.g., `KustoRequestDeniedException`) |
| `failing_test_name` | `str` | Smoke test name if applicable, else `None` |
| `external_service` | `str` | Failing external dependency if applicable |
| `error_code` | `str` | HTTP/error status code (e.g., `403-Forbidden`) |
| `error_summary` | `str` | One-line human-readable summary |

## Processing Logic

1. **Handle empty logs** — If `log_count == 0`, return `error_classification = "no_logs_found"`.

2. **Scan for smoke test failure patterns:**

| Pattern | Indicates |
|---|---|
| `SmokeTest` or `AASmokeTests` | Smoke test framework exception |
| `ParallelTest` + test name | Specific smoke test failure |
| `403-Forbidden` or `Unauthorized` | Auth/permission failure |
| `KustoRequestDeniedException` | Kusto access revoked |
| `CertificateExpiredException` | Certificate rotation needed |

3. **Extract failing test name** — Parse from exception text. Known test names: `RunKustoAccessProductionTest`, `RunKustoAccessNationalCloudTest`, `RunXdsAccessTest`, `RunXlsAccessTest`, `RunMdmAccessTest`, `RunStorageAccessTest`, `RunServiceBusTest`, `RunIcmUpdateIncidentTest`, `RunOnCallClientTest`, `RunXLivesiteDCLoadTest`, `RunMdsAccessTest`, `RunRsrpAccessTest`, `RunHealthServiceAccessTest`.

4. **Extract external service and error code** — Parse `DataSource=<URL>` → `external_service`, HTTP status codes → `error_code`.

5. **Classify non-smoke-test crashes** — Common patterns: `OutOfMemoryException` (memory leak), `StackOverflowException` (infinite recursion), `NullReferenceException` (code bug), `TimeoutException` (dependency hang), `SocketException` (network).

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: None (pure log parsing — no external API calls)
AUTOMATABLE: Yes
MANUAL_FALLBACK: DRI reads DGrep log entries manually, identifies exception type from stack trace text.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is the list of smoke test names exhaustive, or can new tests be added dynamically? |
| 2 | Are there additional exception patterns beyond auth errors that indicate smoke test failures? |
| 3 | What is the exact format of the exception text in `XLivesiteLog`? |
