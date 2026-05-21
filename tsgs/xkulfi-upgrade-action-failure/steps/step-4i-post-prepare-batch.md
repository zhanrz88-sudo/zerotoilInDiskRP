# Step 4i — PostPrepareBatchOperation branch

> **Parent TSG**: [xkulfi-upgrade-action-failure](../xkulfi-upgrade-action-failure.md)
> **Source**: [PostPrepareBatchOperation.md](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/xdeployment/tsg/XPFDeployment/XKulfi/Incidents/UpgradeActionFailure/PostPrepareBatchOperation.md)
> **Maps to**: `_step_4i_post_prepare_batch()`
> **Sample incident**: 739763565

## Purpose

XDS domain preparation completed but XKulfi failed to execute post-UD-prepare steps. Known signature: `KeyNotFoundException` on app version `release/26.0122.1.0` — mitigated by editing the `TenantRolloutInfo` blob XML to inject `UpgradedMachineFunctionMachinesMappings`.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant`, `deployment_id`, `domain`, `target_version` | `str` | Step 1 |
| `dgrep_rows` | `list[dict]` | Step 2 |

## Outputs

| Field | Type | Description |
|---|---|---|
| `error_signature` | `str \| None` | Detected exception type |
| `is_known_keyerror_pattern` | `bool` | True iff signature matches the documented `KeyNotFoundException` + app `release/26.0122.1.0` pattern |
| `tenant_rollout_info_path` | `str` | `xdashxstorepublicpf/xkulfi/TenantStatus/<virtual-tenant>/TenantRolloutInfo` |
| `xml_patch_template` | `str` | Pre-rendered XML block to append below `<UpdatedTime>` |
| `mitigation_summary` | `str` | Detailed manual instruction packet |

## Processing Logic

1. Extract `error_signature` and check for the known pattern: result `Faulted`, exception `System.Collections.Generic.KeyNotFoundException`, app version `release/26.0122.1.0`.
2. If known pattern → emit:
   - blob path `xdashxstorepublicpf/xkulfi/TenantStatus/<tenant>/TenantRolloutInfo`
   - the XML insertion template (verbatim from source TSG, with `XUTLT` block conditional on whether tenant has the `XUTLT` machine function)
   - manual steps: bump `<DateTime>` inside `<UpdatedTime>` to a future UTC, upload-to-replace
3. If unknown signature → escalate as generic.

### XML insertion template (verbatim from source)

```xml
<UpgradedMachineFunctionMachinesMappings xmlns:d2p1="http://schemas.microsoft.com/2003/10/Serialization/Arrays">
    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
        <d2p1:Key>XRSL</d2p1:Key>
        <d2p1:Value></d2p1:Value>
    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
        <d2p1:Key>XUTLT</d2p1:Key>
        <d2p1:Value></d2p1:Value>
    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
        <d2p1:Key>XBE</d2p1:Key>
        <d2p1:Value></d2p1:Value>
    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
    <d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
        <d2p1:Key>XMGMT</d2p1:Key>
        <d2p1:Value></d2p1:Value>
    </d2p1:KeyValueOfstringArrayOfstringty7Ep6D1>
</UpgradedMachineFunctionMachinesMappings>
```

> Remove the `XUTLT` block if the tenant doesn't have an `XUTLT` machine function.

## Automation Assessment

```
CODING_ABILITY_DEPENDENCY:
  - GAP: no coding ability for reading the existing TenantRolloutInfo blob to
    decide if XUTLT block is needed
  - GAP: no coding ability for writing back the XML (intentionally manual —
    edits live tenant rollout state)
AUTOMATABLE: Partially.
  - Detect the known KeyError pattern + render the patch template: Yes.
  - Apply the edit: No (manual upload-to-replace).
MANUAL_FALLBACK: For unknown signatures, escalate via step-4z.
```

## Open Questions

| # | Question |
|---|---|
| 1 | Is the `release/26.0122.1.0` app-version condition still relevant in 2026 builds, or has the underlying bug been fixed? Source TSG dates from early 2026. |
| 2 | How does an automation determine whether the tenant has `XUTLT` machine function without reading the blob? Is there an XDS metadata endpoint? |
