---
name: Geneva Action Translation Layer
description: Translate manual FC Shell, DcM, and portal operations to automatable Geneva Action (GA) calls. Works with both YAML TSGs and raw TSG markdown — use ga-catalog.json to look up the correct GA for any manual operation.
---

# Coding Ability: ga-translation-layer

## Description

Translates manual operations (FC Shell commands, DcM Explorer operations, Geneva Actions portal navigation, manual shell/RDP steps) into automatable **Geneva Action (GA)** calls. Works with two input formats:

1. **Raw TSG / assessed TSG markdown** → generates `acis.execute()` / `acis.submit()` Python code directly
2. **YAML TSG** → replaces manual steps with `GenevaAction:` YAML action type

This coding ability is **self-contained** — copy the entire `ga-translation-layer/` folder to any repo that needs GA translation capabilities.

- **Catalog**: `ga-catalog.json` contains 421 Geneva Actions across all XStore teams with operation IDs, ordered parameters, safety info, team ownership, and keyword mappings for lookup
- **Lookup**: Each GA entry has a `replaces` array of keywords. Match manual operation text against these keywords to find the correct GA.

### Dependencies

- **`geneva-action-call`** coding ability — provides the `acis.execute()` / `acis.submit()` calling pattern used at runtime to invoke GAs programmatically. This translation ability defines *which* GA to use; `geneva-action-call` defines *how* to call it.

## Remarks

### Catalog Lookup (same for both modes)

The `ga-catalog.json` file supports keyword-based lookup via the `replaces` array on each operation. To find the right GA:

1. Extract the manual operation keywords from the TSG step (e.g., "BIOS flavor reset", "power cycle", "set HI", "send to OFR")
2. Search `ga-catalog.json` → `operations[].replaces[]` for matching keywords
3. Filter by `environment` if tenant type is known (XStore, DD, XPF, CrossService)
4. Check `deprecated` — if true, use `deprecated_use_instead`
5. Return the matched operation with its `id`, `parameters`, and `operation_group`

### Environment Routing

When multiple GAs exist for the same operation (e.g., PowerNode exists in FabricCrossService, Kiona, and SustainabilityDelegatedSafe), choose based on tenant type:

```
Is the tenant XPF (PilotFish)?
  ├── Yes → Use Kiona/ GA (requires MachineName, not NodeId)
  └── No
      ├── Direct Drive? → Use DirectDriveDelegatedSafe/ if DD-specific GA exists
      │                    Otherwise use FabricCrossService/ (supports DD + XStore)
      └── XStore Fabric? → Use FabricCrossService/ (preferred)
                           or SustainabilityDelegatedSafe/ if no CrossService version
```

If a GA is marked `deprecated: true` in the catalog, use the GA listed in `deprecated_use_instead`.

---

## Mode 1: Raw TSG / Assessed TSG → Python Code

When generating Python code directly from a raw TSG document (markdown, assessed TSG, or any text describing manual operations), use the catalog to generate `acis.execute()` / `acis.submit()` calls.

### Translation Rules (Raw TSG → Python)

#### Rule 1: GA match found → generate `acis.execute()` / `acis.submit()` code

When the TSG text describes an operation that matches a GA in the catalog, generate the appropriate ACIS call.

**For read-only operations** (e.g., check SAC, get switch port status):
```python
from xportal import acis

# GA: CheckSACConnectionDelegated (read-only)
result = await acis.execute(
    "Xstore",
    "CheckSACConnectionDelegated",
    [tenant_name, node_id, incident_id, ""],
)
print(f"SAC Connection result: {result}")
```

**For mutating operations** (e.g., power cycle, reset health, OFR):
```python
from xportal import acis

# GA: PowerNodeCrossServiceDelegated (mutating — requires approval)
# APPROVAL_GATE: Mutating operation — power cycle node
response = await acis.submit(
    "Xstore",
    "PowerNodeCrossServiceDelegated",
    [tenant_name, "", node_id, "PowerCycle", incident_id, "", "false"],
)
action_id = response["id"]
result = await acis.get_result("Xstore", action_id, wait_for_completion=True)
print(f"Power cycle result: {result}")
```

#### Rule 2: No GA match found → print manual step and raise exception

When the TSG describes an operation with no GA equivalent (e.g., interactive FcShell, PfAgent Shell, DCM Explorer UI), generate a `print()` statement describing the manual action and raise `ManualActionRequired`.

```python
# NO_GA_AVAILABLE: FcShell $n.events is interactive — no API
# Alternative: Query Kusto GetAllStorageNodeFabricHealth for node events
print("MANUAL STEP REQUIRED: Query node events via FcShell")
print("  Command: $f = Get-Fabric <TenantName>; $n = $f | Get-Node '<NodeId>'; $n.events")
print("  Alternative: Use Kusto query on GetAllStorageNodeFabricHealth")
raise ManualActionRequired(
    "FcShell $n.events requires interactive SAW session. "
    "Use Kusto GetAllStorageNodeFabricHealth as automated alternative."
)
```

#### Rule 3: Partial match → generate GA code with surrounding logic

When the TSG mixes a GA operation with validation/branching logic, generate the GA call within the Python logic.

```python
# Check if node is in HI state, then reset health via GA
if tm_state == "HumanInvestigate":
    print("Node is HI — resetting health via Geneva Action")
    # GA: ResetNodeHealthCrossServiceDelegated (mutating)
    # APPROVAL_GATE: Mutating operation — reset node health
    response = await acis.submit(
        "Xstore",
        "ResetNodeHealthCrossServiceDelegated",
        [tenant_name, node_id, "false", incident_id, ""],
    )
    result = await acis.get_result("Xstore", response["id"], wait_for_completion=True)
    print(f"Reset health result: {result}")
else:
    print("Node is not HI — skipping reset")
```

### Key conventions for generated Python code

- **Read-only GAs** → `await acis.execute()` (synchronous, single call)
- **Mutating GAs** → `await acis.submit()` + `await acis.get_result(wait_for_completion=True)` (async with polling)
- **All mutating operations** must have a `# APPROVAL_GATE:` comment before the `acis.submit()` call
- **No GA available** → `print()` describing the manual step + `raise ManualActionRequired(...)` with explanation and alternative
- **GA operation ID and params** come from `ga-catalog.json` — use the `parameters` array in positional order

---

## Mode 2: YAML TSG → GA-enriched YAML

When transforming a YAML TSG, replace manual steps with `GenevaAction:` action type steps.

### Translation Rules (YAML → GA YAML)

#### Rule 1: Full GA replacement → `GenevaAction:` step

When a YAML step is **entirely** a manual GA operation (portal navigation, print instructions, single operation), replace it with a `GenevaAction:` action type.

**Before** (manual portal step):
```yaml
- PyCodeAction:
    Description: Execute BIOS Flavor Reset via Geneva Actions portal
    Code: |
      print("Navigate to Geneva Actions portal:")
      print("  Breadcrumb: Xstore > Sustainability Operations With Delegated Auth - Safe > BiosFlavorResetOperation")
      print(f"  Tenant Name: {self.inputs['TenantName']}")
      print(f"  Node Id: {self.inputs['NodeId']}")
```

**After** (automatable GA step):
```yaml
- GenevaAction:
    Description: Execute BIOS Flavor Reset on the node
    OperationId: BiosFlavorResetCrossServiceDelegated
    Extension: Xstore
    OperationGroup: FabricCrossService
    Parameters:
      tenantName: "{TenantName}"
      clusterName: ""
      nodeId: "{NodeId}"
      incidentId: "{incidentId}"
      incidentCategory: ""
    Mutating: true
    RequiresApproval: true
```

#### Rule 2: Partial replacement → split into `GenevaAction:` + `PyCodeAction:`

When a step mixes GA operations with other logic (validation, branching, result processing), split it into separate steps.

**Before** (mixed step):
```yaml
- PyCodeAction:
    Description: Check node state and reset health if HI
    Code: |
      if self.outputs['TMState'] == 'HumanInvestigate':
        print("Node is HI, resetting health via Geneva Actions portal")
        print("  Breadcrumb: Xstore > Cross Service > Reset Node Health")
        print(f"  Tenant: {self.inputs['TenantName']}, Node: {self.inputs['NodeId']}")
      else:
        print("Node is not HI, skipping reset")
```

**After** (split):
```yaml
- PyCodeAction:
    Description: Check if node is in HI state and set flag for reset
    Code: |
      self.outputs['needs_reset'] = self.outputs['TMState'] == 'HumanInvestigate'
      if self.outputs['needs_reset']:
        print("Node is HI — will reset health")
      else:
        print("Node is not HI — skipping reset")

- GenevaAction:
    Description: Reset node health (only if node was in HI state)
    Condition: "py|self.outputs.get('needs_reset', False)"
    OperationId: ResetNodeHealthCrossServiceDelegated
    Extension: Xstore
    OperationGroup: FabricCrossService
    Parameters:
      tenantName: "{TenantName}"
      nodeId: "{NodeId}"
      shouldSkipSafetyChecks: "false"
      incidentId: "{incidentId}"
      incidentCategory: ""
    Mutating: true
    RequiresApproval: true
```

#### Rule 3: No GA equivalent → keep as `PyCodeAction:` with annotation

When a manual operation has no GA equivalent, keep the original step and annotate it.

```yaml
- PyCodeAction:
    Description: "[MANUAL - No GA equivalent] Check FcShell node events for diagnosis"
    GATranslation: NOT_AVAILABLE
    GATranslationReason: "FcShell $n.events is interactive — no API. Use Kusto node events query as alternative."
    Code: |
      print("MANUAL STEP: Query node events via FcShell")
      print("  Alternative: Use Kusto query on GetAllStorageNodeFabricHealth")
```

### `GenevaAction:` YAML Schema

```yaml
- GenevaAction:
    Description: str           # What this action does
    OperationId: str            # From ga-catalog.json
    Extension: str              # Always "Xstore" for XStore GAs
    OperationGroup: str         # Folder/group name (e.g., FabricCrossService, Kiona)
    Parameters:                 # Ordered dict — maps to positional acis.execute() params
      paramName: "value"        # Use {InputName} for template variables
    Mutating: bool              # true if this changes production state
    RequiresApproval: bool      # true if human approval needed before execution
    Condition: str              # Optional. Python expression — only execute if true
    Label: str                  # Optional. Store result in self.outputs[Label]
    Timeout: int                # Optional. Timeout in seconds (default: 300)
    PostCheck:                  # Optional. Verification after GA completes
      Type: str                 # "KustoQuery" or "PyCode"
      ...
```

---

## Known Gaps (No GA Equivalent)

| Manual Operation | Reason | Workaround |
|---|---|---|
| FcShell `$n.events` (node event query) | Interactive FcShell session | Kusto query on node events |
| FcShell `Get-Image` (image metadata) | Interactive FcShell session | ListOSImages OaaS GA or Kusto |
| DCM Explorer SAC interactive session | UI-based tool | CheckSACConnection GA for basic check |
| PfAgent Shell commands | Interactive shell | Some covered by ExecuteNodeCommand GA |
| Manual ICM UI operations | Portal-only | Use `icm-get-incident` coding ability |

## Sample: Raw TSG → Python Code (FC8 Step 6)

**TSG text**: "Delete OS images while in MOS. Connect to node via PfAgent in DCM Explorer, open Shell tab, navigate to C:\OS, delete all files, then redeploy FullOS."

**Generated Python code**:
```python
# Step 6.1: Boot into MOS
# GA: PutNodeIntoMOSCrossServiceDelegated (mutating)
# APPROVAL_GATE: Mutating operation — boot node into MOS
response = await acis.submit(
    "Xstore", "PutNodeIntoMOSCrossServiceDelegated",
    [cluster_id, tenant_name, node_id, "", "false", incident_id, ""],
)
mos_result = await acis.get_result("Xstore", response["id"], wait_for_completion=True)

# Step 6.2: Delete OS images (replaces PfAgent Shell "cd C:\OS; del *")
# GA: DeleteOSVhdOrAgentPackagesCrossServiceDelegated (mutating)
# APPROVAL_GATE: Mutating operation — delete OS VHD images
response = await acis.submit(
    "Xstore", "DeleteOSVhdOrAgentPackagesCrossServiceDelegated",
    [tenant_name, node_id, "OSVhd", incident_id, ""],
)
delete_result = await acis.get_result("Xstore", response["id"], wait_for_completion=True)

# Step 6.3: Redeploy FullOS (replaces FcShell "Return to FullOS")
# GA: RedeployOSCrossServiceDelegated (mutating)
# APPROVAL_GATE: Mutating operation — redeploy FullOS
response = await acis.submit(
    "Xstore", "RedeployOSCrossServiceDelegated",
    [tenant_name, node_id, incident_id, ""],
)
redeploy_result = await acis.get_result("Xstore", response["id"], wait_for_completion=True)
```

## Sample: YAML TSG Translation (BIOS Flavor Reset)

### Before (original YAML with portal instructions):

```yaml
- PyCodeAction:
    Description: Provide Geneva Actions execution steps for BiosFlavorResetOperation
    Code: |
      print("Navigate to the Geneva Actions portal and execute:")
      print("  Breadcrumb: Xstore > Sustainability Operations > BiosFlavorResetOperation")
      print(f"  Tenant Name: {self.inputs['TenantName']}")
      print(f"  Node Id: {self.inputs['NodeId']}")
```

### After (automatable GenevaAction step):

```yaml
- GenevaAction:
    Description: Execute BIOS Flavor Reset via Geneva Action
    OperationId: BiosFlavorResetCrossServiceDelegated
    Extension: Xstore
    OperationGroup: FabricCrossService
    Parameters:
      tenantName: "{TenantName}"
      clusterName: ""
      nodeId: "{NodeId}"
      incidentId: "{incidentId}"
      incidentCategory: ""
    Mutating: true
    RequiresApproval: true
    Label: bios_reset_result
    Timeout: 600
    Notes: |
      Uses CrossService version (preferred over deprecated SustainabilityDelegatedSafe BiosFlavorReset).
      Node must be Gen6+. Use AC flavor (not GN) as intermediate reset flavor (Secure Boot required).
```
