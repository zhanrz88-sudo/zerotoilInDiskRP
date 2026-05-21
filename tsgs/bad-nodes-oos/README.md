# Taking Bad Role Instances Out of Service — TSG Family

## TSG Call Graph

```
bad-nodes-oos  (TSG class — single source document)
  Step 1 — Request JIT access
  Step 2 — Collect diagnostic logs and check node health
  Step 3 — Restart offending role instances
  Step 4 — Escalate to out-of-service actions
    ├── Quarantine via Geneva Action (short term)
    ├── Set OOS Role Marker via Geneva Action / XDS fallback (medium term)
    ├── Set OOS via DC Geneva Action / XDS DC XML (long term)
    └── Last resort: RDP / FC Shell (fully manual)
  Step 5 — Request MR repair and create follow-up tasks
```

## Design Principles

- One source document = one TSG class. The entire "Taking bad role instances out of service" doc is one class.
- Steps are methods, not separate classes. All OOS approaches (quarantine, OOS marker, OOS via DC) are branches within Step 4, not separate TSGs.
- Every called TSG lives in its own folder under `zero-toil/tsgs/` — this TSG currently has no external TSG calls.
- Step analysis files under `steps/` for per-step automation assessment.
- Decision tree flows: restart first → quarantine → OOS marker → OOS via DC → RDP/FC Shell.
- Mutating Geneva Actions require SAW/dSTS auth — automation can prepare parameters and generate portal links, but execution requires human interaction.

## File Structure

| File | Role |
|---|---|
| `bad-nodes-oos.md` | **TSG** — main class with 5 steps |
| `_references.md` | Shared constants (Geneva Actions, JIT, DGrep events, DC config paths, contacts) |
| `steps/step-1-request-jit-access.md` | Step analysis — JIT acquisition |
| `steps/step-2-collect-diagnostics-and-check-health.md` | Step analysis — log collection, DGrep node health, CPU trace |
| `steps/step-3-restart-role-instances.md` | Step analysis — restart via XDS with dump |
| `steps/step-4-escalate-to-oos-actions.md` | Step analysis — quarantine / OOS marker / OOS via DC / RDP |
| `steps/step-5-request-mr-repair-and-follow-up.md` | Step analysis — MR repair and bug filing |

## Source Documents

| TSG File | Primary Knowledge Base Source |
|---|---|
| `bad-nodes-oos.md` | [Taking bad role instances out of service](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=Frontend_Layer/tsgs/miscellaneous/bad-nodes-oos.md&version=GBmaster) |
