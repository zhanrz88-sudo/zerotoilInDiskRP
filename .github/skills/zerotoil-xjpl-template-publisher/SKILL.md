---
name: zerotoil-xjpl-template-publisher
description: "Publish zerotoil Python modules (.py) as XJPL-compatible Jupyter notebook templates (.ipynb). Converts `from zerotoil.*` imports to `xportal.run_template` calls, preserves stable template_id GUIDs, and skips __init__.py / __pycache__. USE FOR: publish notebook, sync notebooks, convert py to ipynb, publish templates, xjpl publish, sync zerotoil notebooks, publish TSG as notebook."
---

# ZeroToil XJPL Template Publisher

This skill publishes **zerotoil Python modules** as **XJPL-compatible Jupyter notebook templates** so they can be executed in the XPortal Jupyter environment.

## When to apply this skill

- After `tsg-code-writer` generates or updates Python modules under `zerotoil/tsgs/`.
- When you need to re-publish all modules after manual edits to the Python sources.
- When the user asks to "publish", "sync", or "convert" zerotoil code to notebooks.
- When the user asks to publish a specific TSG module as a notebook template.

## What the script does

The conversion script `scripts/sync_zerotoil_notebooks.py`:

1. Scans `zerotoil/` for `.py` files (skipping `__init__.py` and `__pycache__/`)
2. For each `.py` file, generates a `.ipynb` under `jupyter-templates/Xstore/zerotoil/` with the same relative path structure
3. Replaces `from zerotoil.x.y import A, B` imports with `xportal.run_template` calls
4. Adds TSG-only execution wrapper cells: a first code cell with `incident_id = None` and a last code cell that runs the detected TSG class only when `incident_id` is truthy
5. Preserves existing `template_id` GUIDs (reads from existing `.ipynb` if present; generates a new UUID only for new files)

### Mapping example

| Source | Published notebook |
|---|---|
| `zerotoil/core/framework.py` | `jupyter-templates/Xstore/zerotoil/core/framework.ipynb` |
| `zerotoil/tsgs/csm_quorum_loss.py` | `jupyter-templates/Xstore/zerotoil/tsgs/csm_quorum_loss.ipynb` |

### Import transformation example

**Before** (Python module import):
```python
from zerotoil.core.framework import TsgBase, TsgInput
from zerotoil.tsgs.escalate_gdco_tickets import EscalateGdcoTickets, EscalateGdcoTicketsInput
```

**After** (XJPL notebook):
```python
import xportal
exports = await xportal.run_template('/Xstore/zerotoil/core/framework.ipynb', outputs=['TsgBase', 'TsgInput'])
TsgBase = exports['TsgBase']
TsgInput = exports['TsgInput']
exports = await xportal.run_template('/Xstore/zerotoil/tsgs/escalate_gdco_tickets.ipynb', outputs=['EscalateGdcoTickets', 'EscalateGdcoTicketsInput'])
EscalateGdcoTickets = exports['EscalateGdcoTickets']
EscalateGdcoTicketsInput = exports['EscalateGdcoTicketsInput']
```

Non-zerotoil imports (stdlib, `xportal`, `xds_client`, `pydantic`, etc.) are left unchanged.

### TSG notebook wrapper cells

When the source `.py` file defines a class inheriting from `TsgBase`, the published notebook gets two extra code cells:

**First cell**:
```python
incident_id = None
```

**Last cell**:
```python
if incident_id:
   tsg = FailoverPendingTransaction()
   await tsg.run_for_incident(str(incident_id))
```

The publisher detects the concrete TSG class name from the source module, so the final cell uses the correct class for each TSG file.

If the source file is **not** a TSG module (no class inheriting from `TsgBase`), these wrapper cells are **not** added.

## Step-by-step workflow

### Step 1 — Pre-flight check

Before running the script, verify:

1. The source directory `zerotoil/` exists and contains `.py` files.
2. The script `scripts/sync_zerotoil_notebooks.py` exists.
3. If the user specified specific modules, confirm those `.py` files exist.

### Step 2 — Run the conversion script

Execute the script from the repo root:

```bash
cd d:\gitroot\XScript-Templates
& zero-toil\.venv\Scripts\Activate.ps1
python scripts/sync_zerotoil_notebooks.py
```

If publishing specific modules:
```bash
python scripts/sync_zerotoil_notebooks.py csm_quorum_loss
```

### Step 3 — Verify outputs

After the script completes:

1. List the generated `.ipynb` files under `jupyter-templates/Xstore/zerotoil/`.
2. For each generated notebook, confirm:
   - It has a valid `template_id` (UUID) in its metadata.
   - The `from zerotoil.*` imports have been replaced with `xportal.run_template` calls.
   - TSG notebooks have the `incident_id = None` first code cell and the conditional execution last code cell.
   - Non-TSG notebooks do not get those extra cells.
   - Non-zerotoil imports are untouched.
   - The original source file path appears in the markdown cell.
3. If the user asked for specific modules, verify those specific notebooks.

### Step 4 — Report results

Provide a summary:

- Number of files converted
- List of published notebooks with their template_ids
- Any warnings (e.g., syntax errors in source files that prevented import transformation)

## Hard rules (non-negotiable)

- **Never edit generated notebooks manually** — always re-run the script. The notebooks are derived artifacts.
- **Never edit the source `.py` files** — this skill only publishes, it does not modify sources.
- **Preserve template_ids** — if a notebook already exists with a valid UUID template_id, the script keeps it. Do not regenerate IDs for existing notebooks.
- **Do not commit `__init__.py` as notebooks** — they are skipped by design.
- **Do not run the script outside the repo root** — paths are relative to the repo root.

## Troubleshooting

| Problem | Action |
|---|---|
| Script not found | Check path `scripts/sync_zerotoil_notebooks.py` |
| Python not available | Activate the venv: `& .venv/Scripts/Activate.ps1` |
| Syntax error in a `.py` file | The script warns but still produces the notebook (imports won't be transformed). Report the warning to the user. |
| Missing source directory | Verify `zerotoil/` exists. The tsg-code-writer agent must generate the `.py` files first. |

## Pipeline context

This skill is typically invoked **after** TSG code generation:

1. `tsg-document-writer` agent → writes TSG analysis documents
2. `tsg-code-writer` agent → generates `.py` modules from TSG documents
3. **This skill** → publishes `.py` modules as `.ipynb` templates
