# Step 1 — Confirm known signature in primary logs
> **Parent TSG**: [mitigate-xnamespace-directorystatistics-block](../mitigate-xnamespace-directorystatistics-block.md)
> **Maps to**: `_step_1_confirm_signature()` method

## Purpose
Verify the known XNamespaceDirectoryStatistics error signature is present before applying mitigation.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `incident_id` | `int` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `signature_found` | `bool` | Whether the known error text was found |

## Processing Logic
1. Query DGrep or XAC diagnostics around incident window.
2. Search for: `Table:XNamespaceDirectoryStatistics which has not done pairing has data`
3. If absent → return `signature_found=false`, route to general escalation.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: dgrep-query (xportal.dgrep.query)
AUTOMATABLE: Yes
```

## Open Questions
| # | Question |
|---|---|
| 1 | Which log source is canonical: XACServer cosmos or DGrep? |
