---
name: Geneva Action Call (ACIS)
description: Execute Geneva Actions (ACIS operations) via the xportal.acis module — submit, poll, and retrieve results.
---

# Coding Ability: geneva-action-call

## Description

Executes Geneva Actions (internally called ACIS — Azure Configuration and Infrastructure Services) using the `xportal.acis` module. Geneva Actions invoke operations on XStore tenants such as node recovery, config changes, partition operations, and GDCO ticket management.

- **Safety-critical**: Geneva Actions can mutate production state (power cycle nodes, change configs, trigger repairs). Gate all mutating calls behind human approval.
- Read-only actions (e.g., diagnostic queries) are safe for automation.
- In browser (SAW): uses delegated auth with user permissions.
- In automation: uses cert `StoragePlatformServiceViewer` — **can only execute READ-ONLY actions**.
- For curated patterns grouped by operation type, see `references/` under this coding ability folder.

Key concepts

- **Extension name**: The ACIS extension that hosts the operation (e.g., `"Xstore"`, `"Sustainability Operations - Safe"`).
- **Operation ID**: The specific operation to invoke (e.g., `"ResetNodeHealthWithSafetyChecksCrossServiceDelegated"`, `"TriggerScrubber"`).
- **Params**: A `list[str]` of positional parameters. Order matters — it matches the Geneva Action parameter order.
- **Endpoint**: Optional. If `None`, uses the first available. Can be `"Production"` or a specific endpoint.
- **Two execution modes**:
  - `acis.execute()` — synchronous: submits and waits for the result in one call.
  - `acis.submit()` + `acis.get_result()` — asynchronous: submit, get a response ID, then poll for the result.

Prereqs

- Run inside an environment where `xportal` is available (XPortal Jupyter / XScript runtime).
- For mutating actions in browser: dSTS auth on SAW required (AAD auth not supported).
- For mutating actions in automation: requires appropriate cert beyond `StoragePlatformServiceViewer`.

## Remarks

Interfaces (from `zero-toil/.venv/Lib/site-packages/xportal/acis.py`)

### `acis.execute()` — synchronous execution

```python
await acis.execute(
    extension_name: str,
    operation_id: str,
    params: List[str],
    endpoint: Optional[str] = None,
    environment: Optional[str] = None,
) -> Any  # JSON result
```

- Submits the action AND waits for the result in a single call.
- Returns the JSON result directly.
- Use for quick, typically read-only operations.

### `acis.submit()` — asynchronous submission

```python
await acis.submit(
    extension_name: str,
    operation_id: str,
    params: List[str],
    endpoint: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict  # contains 'id' key for tracking
```

- Submits the action and returns a response dict with `response['id']` for tracking.
- Use for long-running or mutating operations where you need to poll.

### `acis.get_result()` — poll for result

```python
await acis.get_result(
    extension_name: str,
    response_id: str,
    wait_for_completion: bool = False,
    environment: Optional[str] = None,
) -> Any  # JSON result
```

- `response_id`: The ID from `submit()` response.
- `wait_for_completion=True`: Keeps retrying until the action completes or client timeout.
- `wait_for_completion=False` (default): Returns immediately; throws 404 if not completed yet.

### Environment values

`"Production"` (default), `"Mooncake"`, `"Fairfax"`, `"USNat"`, `"USSec"`.

### Common extension names (from jupyter-templates)

| Extension | Used for |
|---|---|
| `Xstore` | Node recovery, config updates, scrubber, XDiag, partition operations, rebootstrap |
| `Sustainability Operations - Safe` | GDCO ticket severity changes |

### Common operation IDs

**Validated via real `acis.execute()` / `acis.submit()` calls in jupyter-templates:**

| OperationId | Extension | Purpose | Mutating? | Source notebook |
|---|---|---|---|---|
| `TriggerScrubber` | `Xstore` | Trigger scrubber on a partition | Yes | jupyter-templates/Xstore/XTable/XBlob/WGDataIntegrityViolationXblocksChunkExtentMissingRunbook.ipynb |
| `RunXDiagCmdLet` | `Xstore` | Run XDiag commands (partition ops, GC bypass) | Varies | jupyter-templates/Xstore/XTable/GC/PartitionOperations.ipynb |
| `XConfigImmediateManualOrchestration` | `Xstore` | Apply config changes immediately | Yes | jupyter-templates/Xstore/XTable/XBlob/LifespanPrediction/LifespanPredictionConfigUpdate.ipynb |
| `XConfigManualOrchestration` | `Xstore` | Apply config changes with walk-through | Yes | jupyter-templates/Xstore/XTable/XBlob/AutoRevertAnomalousConfigs.ipynb |
| `XBBCapacityAutoMitigation` | `Xstore` | XBB capacity auto-mitigation | Yes | jupyter-templates/Xstore/XTable/XBlob/AutomaticXBBCapacityManagement/ICMAutomationToTriggerXBB.ipynb |
| `BrainPhynetTorHealthForNodeIdParameterized` | `Xstore` | Diagnostic: TOR health for a node | No | xportal/acis.py docstring example (validated API source) |
| `RunXDiagCmdLetScript` | `Xstore` | Run XDiag PowerShell script | Varies | jupyter-templates/Xstore/XInvestigator/XJupyterLite/RunXDiagcmdletExample.ipynb |

**Referenced in notebooks but no direct `acis.execute()`/`acis.submit()` call found (operation IDs confirmed, parameter order NOT validated):**

| OperationId | Extension | Purpose | Source |
|---|---|---|---|
| `ResetNodeHealthWithSafetyChecksCrossServiceDelegated` | `Xstore` | Reset HI node health | jupyter-templates/Xstore/XSSE/XCopilot/XSSEAgentInstructions.ipynb (reference only) |
| `PowerNodeWithSafetyChecksDelegated` | `Xstore` | Power cycle a node | jupyter-templates/Xstore/XSSE/XCopilot/XSSEAgentInstructions.ipynb (reference only) |
| `PutNodeIntoMOSWithSafetyChecksCrossServiceDelegated` | `Xstore` | Put node into MOS | jupyter-templates/Xstore/XSSE/XCopilot/GenevaAction.ipynb (hyperlink gen only) |
| `GDCOChangeSeverity` | `Sustainability Operations - Safe` | Change GDCO ticket severity | TSG docs only — no notebook found |

**Validated via real `acis.execute()` / `acis.submit()` calls on 2026-05-19 (DiskRP operations under `Compute Platform Disks`):**

| OperationId | Extension | Purpose | Mutating? | Endpoint | Params |
|---|---|---|---|---|---|
| `GetDisk` | `Compute Platform Disks` | Get disk metadata + internal XStore fields | No | `Prod` | `[sub, region, rg, diskName]` |
| `GetSnapshot` | `Compute Platform Disks` | Get snapshot metadata + storage account, ISF | No | `Prod` | `[sub, region, rg, snapshotName]` |
| `GetStorageAccount` | `Compute Platform Disks` | Get storage account + all disks/snapshots on it | No | `Prod` | `[sub, region, storageAccountName, apiVersion]` |
| `RemoveIncrementalSnapshotFamilyOnDisk` | `Compute Platform Disks` | Break ISF on a disk | Yes | `Prod` (dSTS) / `Production` (AKS) | `[sub, region, rg, diskName, skipValidation, clearBilling, apiVersion]` |

> **Important:** `Compute Platform Disks` ops require `Prod` endpoint on SAW/dSTS but `Production` on backend AKS worker. The old `Xstore/RunXDiagCmdLetScript` is **DISABLED**. See `coding-abilities/diskrp-acis-operations/ABILITY.md` for full details.

## Sample Python code

```python
from xportal import acis

extension_name = "<extension_name>"  # e.g. "Xstore"
operation_id = "<operation_id>"      # e.g. "ResetNodeHealthWithSafetyChecksCrossServiceDelegated"

# --- Synchronous (simple, for read-only or quick actions) ---
result = await acis.execute(
    extension_name,
    operation_id,
    ["<param1>", "<param2>", "<param3>"],
)
print(result)

# --- Asynchronous (for long-running / mutating actions) ---
response = await acis.submit(
    extension_name,
    operation_id,
    ["<param1>", "<param2>", "<param3>"],
    endpoint="Production",
)
action_id = response["id"]
print(f"Submitted. Action ID: {action_id}")

# Poll for result
result = await acis.get_result(extension_name, action_id, wait_for_completion=True)
print(result)
```
