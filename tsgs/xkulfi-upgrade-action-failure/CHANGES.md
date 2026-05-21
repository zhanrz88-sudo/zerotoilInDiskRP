# Change Note: Add XKulfi UpgradeActionFailure TSG decomposition

**Date:** 2026-04-29
**Author:** ywei
**Commit(s):** _pending_
**TSG / Component:** `zero-toil/tsgs/xkulfi-upgrade-action-failure/`

---

## Why (Motivation)

Draft a decomposed TSG for the XKulfi `UpgradeActionFailure` incident family so it can be automated under `zerotoil/tsgs/`.

- **Trigger:** User request to draft TSG from
  `Storage-XStore-Docs` → `xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/index.md`
  and its sibling per-operation pages.
- **Impact if not done:** Operators continue to manually triage XKulfi `XKulfiAutoAlert` incidents
  with no shared automation, repeating the same DGrep / XDS UI / blob lookups per operation.

## Where (Files Changed)

| File | Type | Summary |
|------|------|---------|
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/xkulfi-upgrade-action-failure.md` | Added | Main TSG: operation matrix, config knobs, routing |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/README.md` | Added | Call graph, design principles, source map |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/_references.md` | Added | Storage account, table schema, escalation contacts, sample incidents |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-1-parse-incident.md` | Added | Parse tenant/operation/rollout from ICM title |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-2-fetch-failure-logs.md` | Added | DGrep `XKulfiAutoAlert` pull + history XML |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-3-route-by-operation.md` | Added | Operation → branch dispatch table |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4a-prepare-batch.md` | Added | `PrepareBatchOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4b-schedule-xcompute.md` | Added | `ScheduleXComputeJobsOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4c-update-stg-version.md` | Added | `UpdateStgVersionOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4d-check-role-ping-after.md` | Added | `CheckRolePingAfterUnprepareOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4e-check-role-ping-before.md` | Added | `CheckRolePingBeforeUnprepareOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4f-check-roles-alteration.md` | Added | `CheckRolesAlterationOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4g-deploy-secrets.md` | Added | `DeploySecretsOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4h-monitor-upgrade-batch-progress.md` | Added | `MonitorUpgradeBatchProgressOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4i-post-prepare-batch.md` | Added | `PostPrepareBatchOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4j-smoke-test.md` | Added | `SmokeTestOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4k-validate-build.md` | Added | `ValidateBuildOperation` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4l-validate-rollout-entity.md` | Added | `ValidateRolloutEntity` branch |
| `zero-toil/tsgs/xkulfi-upgrade-action-failure/steps/step-4z-generic-escalation.md` | Added | Fallback for operations without dedicated source pages |

## What (Major Logic)

### Phase 1 only — decomposition, no Python code

Markdown decomposition follows the `tsg-end-to-end-automation` skill: main overview + per-step files
with `CODING_ABILITY_DEPENDENCY` and `AUTOMATABLE` metadata. Each step file lists open questions for
the code-writer agent to resolve before code generation.

### Routing

Step 3 dispatches by parsing the operation name from the ICM title (`[<Operation>=<DeploymentId>]`
pattern). 12 operations have dedicated branches; 7 remaining operations from `index.md` and any
unparseable title fall through to `step-4z-generic-escalation`.

### Manual-action gating

Mutating operations from the source TSG are intentionally kept manual:
- XDS UI "Skip Current Task" (Advanced Operations) — Step 4a
- `DynamicSettingConfig` table writes — Steps 4b/4c/4d/4e/4f/4g/4h/4j/4k
- Signed XML PRs in `Azure-Gold-Config` / `Storage-XKulfi` — Step 4l

These should remain behind explicit operator approval gates when code is generated.

## Validated

- [x] Decomposition produced via `tsg-document-writer` agent against fetched source pages
- [ ] Phase 2 (coding-ability gap analysis) — not started
- [ ] Phase 3 (code generation) — not started
- [ ] Phase 4 (unit tests) — not started

## Pending / Open Questions

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | Table name `DynamicSettingConfig` vs `DynamicConfigSetting` | High | Source pages use both spellings inconsistently |
| 2 | Virtual tenant resolution for ZRS — already covered by `storage-account-tenant-metadata`? | High | Needed by blob path and DGrep tenant filter |
| 3 | Exact DGrep namespace/table for `XKulfiAutoAlert` | High | Step 2 parameterization |
| 4 | XML blob read coding ability (`xdashxstorepublicpf/xkulfi/TenantStatus/...`) | Med | New ability needed |
| 5 | XDS `UpgradeStateApi` (current preparation task) | Med | Step 4a verification |
| 6 | XDS smoke history endpoint via `xds-api-call` | Med | Steps 4h, 4j |
| 7 | XTS watchdog errors per machine + Trigger manual repair Geneva Action | Med | Step 4h |
| 8 | Current STG version per tenant for downgrade detection | Low | Step 4k |
| 9 | Secrets manifest diff between STG builds | Low | Step 4g |
| 10 | Rollout-trigger metadata | Low | Step 4f |
| 11 | ICM oncall lookup for `XStore/Deployment` | Low | Step 4z `@mention` |
| 12 | `release/26.0122.1.0` KeyError pattern still active in 2026 builds? | Low | Step 4i |

## Assets

_None yet. Will be populated when Phase 2/3 produce coding abilities and generated code._

### Backend job submissions

_None yet — Phase 1 is documentation only._
