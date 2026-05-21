# Storage Node Recovery TSG Family

## TSG Call Graph

```
storage-node-recovery  (TSG class — dispatch)
  Step 1 — Acquire JIT access
  Step 2 — Verify preconditions
  Step 3 — Dispatch to fault-code-specific TSG
    ├── [calls TSG] storage-node-recovery-fc-8  (separate folder — FC 8 recovery)
    ├── [calls TSG] storage-node-recovery-fc-70007  (separate folder — FC 70007 recovery)
    └── [calls TSG] storage-node-recovery-fc-43030  (separate folder — FC 43030 recovery)
  Step 4 — Generic recovery fallback (unknown fault codes)
```

## Design Principles

- One source document = one TSG class. The parent doc (JIT + Precautions + Dispatch) is one class.
- Each fault-code-specific TSG is a separate source document and gets its own folder.
- This family is called by many incident TSGs (CSM quorum loss, DU, utility roles, etc.).

## File Structure

| File | Role |
|---|---|
| `storage-node-recovery.md` | **TSG** — dispatch class with 4 steps |
| `_references.md` | Shared constants (Geneva Actions, Kusto endpoints, JIT, contacts) |
| `steps/step-1-acquire-jit-access.md` | Step analysis for Step 1 |
| `steps/step-2-verify-preconditions.md` | Step analysis for Step 2 |
| `steps/step-3-dispatch-by-fault-code.md` | Step analysis for Step 3 |
| `steps/step-4-generic-recovery.md` | Step analysis for Step 4 |

## Related TSG Folders (fault-code-specific children)

| Folder | Source Document |
|---|---|
| `storage-node-recovery-fc-8/` | [FC 8 — Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%208%20-%20Node%20Recovery.md&_a=preview) |
| `storage-node-recovery-fc-70007/` | [FC 70007 — Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%2070007%20-%20Node%20Recovery.md&_a=preview) |
| `storage-node-recovery-fc-43030/` | [FC 43030 — Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%2043030%20-%20Node%20Recovery.md&_a=preview) |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `storage-node-recovery.md` | [Storage Node Recovery — JIT Access and Precautions](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/Storage%20Node%20Recovery.md&_a=preview) |
