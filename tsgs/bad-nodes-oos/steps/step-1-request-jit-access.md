# Step 1 — Request JIT access

> **Parent TSG**: [bad-nodes-oos](../bad-nodes-oos.md)
> **Maps to**: `_step_1_request_jit_access()` method

## Purpose
Request JIT (Just-In-Time) access for the offending tenant before executing any diagnostic or mitigation actions.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | TSG input |
| `cloud_environment` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `jit_acquired` | `bool` | Whether JIT was successfully acquired |
| `jit_level` | `str` | Level granted: `PlatformServiceOperator` or `DynamicConfigUpdateRole` |

## Processing Logic
1. Navigate to the JIT portal:
   - Public cloud: [aka.ms/JIT](https://aka.ms/JIT)
   - Non-public clouds: use the cloud-specific portal per [aka.ms/jit](https://aka.ms/jit)
2. Request XDS access with `Storage-PlatformServiceOperator` for `<tenant_name>`.
3. If OOS via DC (Step 4, Option C) may be needed, also request `Storage-DynamicConfigUpdateRole`.
4. Wait for approval.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: None (JIT portal is manual)
AUTOMATABLE: No (JIT approval requires human interaction via portal)
MANUAL_FALLBACK: Use JIT portal directly. Automation can generate the JIT portal URL with pre-filled parameters.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can JIT access be requested programmatically via an API, or is it always portal-based? |
| 2 | What is the typical approval time for PlatformServiceOperator vs DynamicConfigUpdateRole? Should we request both upfront or DynamicConfigUpdateRole only when needed? |
