# Step 3 — Route by operation

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Maps to**: `_step_3_route_by_operation()`

## Purpose

Pure dispatch: pick the per-operation branch in Step 4 based on the parsed operation name.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `operation` | `str \| None` | Step 1 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `branch` | `str` | One of: `prepare-batch`, `schedule-xcompute`, `update-stg-version`, `check-role-ping-after`, `check-role-ping-before`, `check-roles-alteration`, `deploy-secrets`, `monitor-upgrade-batch-progress`, `post-prepare-batch`, `smoke-test`, `validate-build`, `validate-rollout-entity`, `generic` |

## Processing Logic

```
ROUTES = {
    "PrepareBatchOperation":                "prepare-batch",
    "ScheduleXComputeJobsOperation":        "schedule-xcompute",
    "UpdateStgVersionOperation":            "update-stg-version",
    "CheckRolePingAfterUnprepareOperation": "check-role-ping-after",
    "CheckRolePingBeforeUnprepareOperation":"check-role-ping-before",
    "CheckRolesAlterationOperation":        "check-roles-alteration",
    "DeploySecretsOperation":               "deploy-secrets",
    "MonitorUpgradeBatchProgressOperation": "monitor-upgrade-batch-progress",
    "PostPrepareBatchOperation":            "post-prepare-batch",
    "SmokeTestOperation":                   "smoke-test",
    "ValidateBuildOperation":               "validate-build",
    "ValidateRolloutEntityOperation":       "validate-rollout-entity",
}
branch = ROUTES.get(operation, "generic")
```

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY: none (pure dict lookup)
AUTOMATABLE: Yes.
MANUAL_FALLBACK: n/a (the "generic" branch is itself the fallback).
```

## Open Questions

| # | Question |
|---|---|
| 1 | Should operations from the index list that lack a per-operation TSG (e.g., `TenantHealthSignOffOperation`, `CheckOSVersionMismatchedOperation`) get their own future-stub branches, or remain bundled under `generic`? |
