# GDCO Ticket Geneva Actions

**Status**: No notebook was found that calls `acis.execute()` or `acis.submit()` with `GDCOChangeSeverity`. The operation ID is referenced in TSG documentation only.

## Confirmed operation ID (from TSG docs, not from any notebook)

| OperationId | Extension | Source |
|---|---|---|
| `GDCOChangeSeverity` | `Sustainability Operations - Safe` | zero-toil/tsgs/csm-quorum-loss/_references.md (documentation only) |

## Open gap

No jupyter-template was found that invokes `GDCOChangeSeverity` via `xportal.acis`. The operation and its parameter order have not been validated via any existing notebook execution. A real acis call would need to be tested before being used in automation.
