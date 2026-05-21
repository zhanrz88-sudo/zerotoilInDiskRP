# XKulfi UpgradeActionFailure

TSG family for the XKulfi `UpgradeActionFailure` incident — raised when any `UpgradeAction` job exceeds its `RetryCountBeforeAlert` threshold during STG rollout, AP service rollout, or OS upgrade.

## TSG Call Graph

```
xkulfi-upgrade-action-failure  (TSG class)
  Step 1 — Parse incident                   → steps/step-1-parse-incident.md
  Step 2 — Fetch failure logs               → steps/step-2-fetch-failure-logs.md
  Step 3 — Route by operation               → steps/step-3-route-by-operation.md
  Step 4 — Operation-specific branch:
    ├── PrepareBatchOperation                → steps/step-4a-prepare-batch.md
    ├── ScheduleXComputeJobsOperation        → steps/step-4b-schedule-xcompute.md
    ├── UpdateStgVersionOperation            → steps/step-4c-update-stg-version.md
    ├── CheckRolePingAfterUnprepareOperation → steps/step-4d-check-role-ping-after.md
    ├── CheckRolePingBeforeUnprepareOperation→ steps/step-4e-check-role-ping-before.md
    ├── CheckRolesAlterationOperation        → steps/step-4f-check-roles-alteration.md
    ├── DeploySecretsOperation               → steps/step-4g-deploy-secrets.md
    ├── MonitorUpgradeBatchProgressOperation → steps/step-4h-monitor-upgrade-batch-progress.md
    ├── PostPrepareBatchOperation            → steps/step-4i-post-prepare-batch.md
    ├── SmokeTestOperation                   → steps/step-4j-smoke-test.md
    ├── ValidateBuildOperation               → steps/step-4k-validate-build.md
    ├── ValidateRolloutEntityOperation       → steps/step-4l-validate-rollout-entity.md
    └── (other / unknown)                    → steps/step-4z-generic-escalation.md
  Step 5 — Summarize and escalate           (inline)
```

## Design Principles

- One source document = one TSG class. The XKulfi UpgradeActionFailure family has an `index.md` plus per-operation siblings in the same folder; together they describe one triage flow with a routing fan-out, so they collapse into a single TSG class with a router step.
- Steps are methods on the class, not separate classes.
- Each per-operation branch is a step analysis file under `steps/`, mapped to a `_step_4_<operation>()` method.
- All write actions (DynamicSettingConfig table inserts, blob XML edits, "Skip Current Task" UI clicks, repo PRs) are documented but **manual-only by default**. Automation is read-only triage + evidence package.

## File Structure

| File | Role |
|---|---|
| [xkulfi-upgrade-action-failure.md](xkulfi-upgrade-action-failure.md) | Main TSG class |
| [_references.md](_references.md) | Shared constants, contacts, links |
| [steps/step-1-parse-incident.md](steps/step-1-parse-incident.md) | Parse incident title |
| [steps/step-2-fetch-failure-logs.md](steps/step-2-fetch-failure-logs.md) | DGrep + blob log fetch |
| [steps/step-3-route-by-operation.md](steps/step-3-route-by-operation.md) | Operation routing table |
| [steps/step-4a-prepare-batch.md](steps/step-4a-prepare-batch.md) | PrepareBatchOperation branch |
| [steps/step-4b-schedule-xcompute.md](steps/step-4b-schedule-xcompute.md) | ScheduleXComputeJobsOperation branch |
| [steps/step-4c-update-stg-version.md](steps/step-4c-update-stg-version.md) | UpdateStgVersionOperation branch |
| [steps/step-4d-check-role-ping-after.md](steps/step-4d-check-role-ping-after.md) | CheckRolePingAfterUnprepareOperation branch |
| [steps/step-4e-check-role-ping-before.md](steps/step-4e-check-role-ping-before.md) | CheckRolePingBeforeUnprepareOperation branch |
| [steps/step-4f-check-roles-alteration.md](steps/step-4f-check-roles-alteration.md) | CheckRolesAlterationOperation branch |
| [steps/step-4g-deploy-secrets.md](steps/step-4g-deploy-secrets.md) | DeploySecretsOperation branch |
| [steps/step-4h-monitor-upgrade-batch-progress.md](steps/step-4h-monitor-upgrade-batch-progress.md) | MonitorUpgradeBatchProgressOperation branch |
| [steps/step-4i-post-prepare-batch.md](steps/step-4i-post-prepare-batch.md) | PostPrepareBatchOperation branch |
| [steps/step-4j-smoke-test.md](steps/step-4j-smoke-test.md) | SmokeTestOperation branch |
| [steps/step-4k-validate-build.md](steps/step-4k-validate-build.md) | ValidateBuildOperation branch |
| [steps/step-4l-validate-rollout-entity.md](steps/step-4l-validate-rollout-entity.md) | ValidateRolloutEntityOperation branch |
| [steps/step-4z-generic-escalation.md](steps/step-4z-generic-escalation.md) | Unknown operation fallback |

## Source Documents

| Source (ADO `Storage-XStore-Docs`) | TSG file |
|---|---|
| `xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/index.md` | [xkulfi-upgrade-action-failure.md](xkulfi-upgrade-action-failure.md), [_references.md](_references.md) |
| `.../UpgradeActionFailure/PrepareBatchOperation.md` | [steps/step-4a-prepare-batch.md](steps/step-4a-prepare-batch.md) |
| `.../UpgradeActionFailure/ScheduleXComputeJobsOperation.md` | [steps/step-4b-schedule-xcompute.md](steps/step-4b-schedule-xcompute.md) |
| `.../UpgradeActionFailure/UpdateStgVersionOperation.md` | [steps/step-4c-update-stg-version.md](steps/step-4c-update-stg-version.md) |
| `.../UpgradeActionFailure/CheckRolePingAfterUnprepareOperation.md` | [steps/step-4d-check-role-ping-after.md](steps/step-4d-check-role-ping-after.md) |
| `.../UpgradeActionFailure/CheckRolePingBeforeUnprepareOperation.md` | [steps/step-4e-check-role-ping-before.md](steps/step-4e-check-role-ping-before.md) |
| `.../UpgradeActionFailure/CheckRolesAlterationOperation.md` | [steps/step-4f-check-roles-alteration.md](steps/step-4f-check-roles-alteration.md) |
| `.../UpgradeActionFailure/DeploySecretsOperation.md` | [steps/step-4g-deploy-secrets.md](steps/step-4g-deploy-secrets.md) |
| `.../UpgradeActionFailure/MonitorUpgradeBatchProgressOperation.md` | [steps/step-4h-monitor-upgrade-batch-progress.md](steps/step-4h-monitor-upgrade-batch-progress.md) |
| `.../UpgradeActionFailure/PostPrepareBatchOperation.md` | [steps/step-4i-post-prepare-batch.md](steps/step-4i-post-prepare-batch.md) |
| `.../UpgradeActionFailure/SmokeTestOperation.md` | [steps/step-4j-smoke-test.md](steps/step-4j-smoke-test.md) |
| `.../UpgradeActionFailure/ValidateBuildOperation.md` | [steps/step-4k-validate-build.md](steps/step-4k-validate-build.md) |
| `.../UpgradeActionFailure/ValidateRolloutEntityOperation.md` | [steps/step-4l-validate-rollout-entity.md](steps/step-4l-validate-rollout-entity.md) |
