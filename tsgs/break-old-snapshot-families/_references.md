# References: Break Old Snapshot Families

## Geneva Action Details

| Field | Value |
|---|---|
| Extension | Xstore |
| Operation | RunXDiagCmdLetScript (likely) or RunXDiagCmdLet |
| Cmdlet | Invoke-RemoveIncrementalSnapshotFamilyOnDisk |
| JIT Role | PlatformServiceOperator |
| Mutating | Yes |

## Error Patterns

| Error | Cause | Action |
|---|---|---|
| JIT access denied | Missing PlatformServiceOperator role | Acquire JIT before retrying |
| Disk not found | Invalid DiskName/SubscriptionId/ResourceGroup | Verify parameters |
| Action timeout | Long-running operation | Poll with acis.get_result() |

## Escalation

- Disk Service on-call: `AZURERT\DiskService` (team ID: 28322)
- For ClearBilling questions: escalate to PM
