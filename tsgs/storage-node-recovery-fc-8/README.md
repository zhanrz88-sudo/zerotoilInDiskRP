# FC 8 — Storage Node Recovery

## TSG Call Graph

```
fc-8-node-recovery  (TSG class)
  Step 1 — Verify network connectivity and SAC responsiveness
  Step 2 — Simple recovery (Reboot and Reset Health)
  Step 3 — Boot into MOS and redeploy OS
  Step 4 — Delete OS images in MOS and escalate
```

## File Structure

| File | Role |
|---|---|
| `fc-8-node-recovery.md` | **TSG** — main class with 4 steps |
| `steps/step-1-verify-connectivity.md` | Step analysis for Step 1 |
| `steps/step-2-simple-recovery.md` | Step analysis for Step 2 |
| `steps/step-3-mos-recovery.md` | Step analysis for Step 3 |
| `steps/step-4-delete-os-and-escalate.md` | Step analysis for Step 4 |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `fc-8-node-recovery.md` | [FC 8 — Node Recovery](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xSSE/TSGs/Storage%20Node%20Recovery/FC%208%20-%20Node%20Recovery.md&_a=preview) |
