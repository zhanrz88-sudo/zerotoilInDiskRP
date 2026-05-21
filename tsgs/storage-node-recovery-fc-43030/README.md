# FC 43030 — Storage Node Recovery

## TSG Call Graph
```
fc-43030-node-recovery  (TSG class)
  Step 1 — Classify disk fault type
  Step 2 — Execute fault-type-specific mitigation
    └── [calls TSG] escalate-gdco-tickets (for GDCO tickets)
```

## File Structure
| File | Role |
|---|---|
| `fc-43030-node-recovery.md` | **TSG** — main class with 2 steps |
| `steps/step-1-classify-fault-type.md` | Step analysis |
| `steps/step-2-execute-mitigation.md` | Step analysis |

## Source Documents
| TSG File | Source |
|---|---|
| `fc-43030-node-recovery.md` | [FC 43030 — Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%2043030%20-%20Node%20Recovery.md&_a=preview) |
