---
name: learn-coding-ability-required-by-tsgs
description: "Analyzes a TSG folder to find automation gaps, then discovers and documents the coding abilities needed to close those gaps by studying .venv sources and jupyter-templates usage. USE FOR: TSG automation gap analysis, find missing coding abilities, learn API for TSG automation, close automation gaps, prepare coding abilities from TSG requirements."
---

# Learn Coding Abilities Required by TSGs

This skill takes a TSG folder as input, identifies what coding abilities are missing for automation, then systematically discovers the required APIs from `.venv` and `jupyter-templates/` to create or update coding abilities and update the TSGs with accurate dependency information.

## When to apply this skill

- A TSG folder exists under `tsgs/<tsg-family-id>/` and you want to improve its automation readiness.
- TSG files have `CODING_ABILITY_DEPENDENCY: None` or reference tools/APIs with no existing coding ability.
- You want to identify which TSG steps can be automated and which remain manual.

## Inputs

1. **TSG folder path** (required) — e.g., `tsgs/csm-quorum-loss/`
2. **Coding ability scope** (optional) — focus on a specific API or tool (e.g., "Geneva Actions", "XDS role pings"). If not specified, analyze all gaps.

## Methodology (6 phases)

### Phase 1 — Inventory TSG automation gaps

1. Read every TSG `.md` file in the folder (skip `README.md` and `_references.md`).
2. For each TSG, extract:
   - `CODING_ABILITY_DEPENDENCY` — what's currently listed.
   - `AUTOMATABLE` — current assessment.
   - Steps that reference external tools/APIs (Kusto, XDS, Geneva Actions, DGrep, ICM, etc.).
   - Open Questions that ask "can X be done programmatically?"
3. Cross-reference against `coding-abilities/README.md` — which coding abilities already exist?
4. Produce a **gap table**: TSG file → tool/API needed → existing coding ability (or "missing").

### Phase 2 — Prioritize gaps

For each missing coding ability:
- How many TSGs need it?
- Is it read-only (safe) or mutating (needs approval gates)?
- Is the underlying API likely to exist in `.venv` or `jupyter-templates/`?

Focus on the highest-impact gaps first.

### Phase 3 — Discover the API

For each prioritized gap, follow the learn-xds-api-coding-ability methodology:

1. **Find the module**: search `.venv/Lib/site-packages/` for related packages.
   - Search by code name (e.g., `acis` for Geneva Actions, `xds_client` for XDS).
   - Search by functional name (e.g., `geneva`, `kusto`, `dgrep`).
   ```
   Get-ChildItem ".venv/Lib/site-packages" -Directory -Filter "*<keyword>*"
   ```

2. **Read the source**: extract function signatures, parameter types, return types from `.venv`.
   - Read `__init__.py` for exports.
   - Read key module files for function signatures and docstrings.
   - For Swagger-generated clients: read `swagger_types` in model files.

3. **Find real usage**: grep `jupyter-templates/**/*.ipynb` for actual `await` calls.
   ```
   grep_search: "from <module> import|import <module>" in jupyter-templates/**/*.ipynb
   ```

4. **Read the notebooks**: extract the exact call patterns, parameter values, result handling.

5. **Cross-reference**: verify notebook usage matches `.venv` source signatures.

### Phase 4 — Create or update coding abilities

For each gap that has a discoverable API:

1. Create `coding-abilities/<coding-ability-id>/ABILITY.md` following the standard structure.
2. Create `references/` files grouped by operation type.
3. **Critical validation rule**: every code example must come from one of:
   - A real `await` call in an existing jupyter-template (cite the notebook path).
   - A function signature in `.venv` source code (cite the file).
   - An official snippet in `jupyter-snippets/public.json`.
4. If an operation is referenced in TSG docs but NOT found in any notebook or `.venv`:
   - List it in a "Referenced but not validated" section.
   - Do NOT invent `await` calls with guessed parameters.
   - Flag the open gap explicitly.

### Phase 5 — Update TSG documents

For each TSG that now has a matching coding ability:

1. Update `CODING_ABILITY_DEPENDENCY` to list the new coding-ability-id (with specific API methods in parentheses).
2. Update `AUTOMATABLE` assessment if the gap was closed.
3. Resolve Open Questions that are answered by the new coding ability:
   - Keep the original question text (strikethrough).
   - Append `**Resolved**: <answer citing the coding-ability-id and method>`.
   - **Never delete the original question** — preserve the audit trail.
4. For gaps that remain (no API found, or unvalidated operations):
   - Keep `CODING_ABILITY_DEPENDENCY` as-is or note "not validated".
   - Add new Open Questions if the research revealed new unknowns.

### Phase 6 — Update indexes

1. Add new coding abilities to `coding-abilities/README.md`.
2. Add new coding abilities to `docs/tsg_coding_abilities.md`.

## Validation rules (non-negotiable)

- **Never invent API calls.** If no notebook calls an operation directly, say so.
- **Always cite sources.** Every reference example must have a "Source:" or "Inspired by:" line.
- **Distinguish validation levels:**
  - ✅ **Validated**: real `await` call found in a notebook.
  - 🔶 **API source validated**: signature confirmed from `.venv`, but no notebook usage.
  - ⚠️ **Documentation-only**: operation referenced in TSG/KB docs, not in code. Parameter order unknown.
- **Never modify TSG steps or requirements** — only update Automation Notes, Open Questions, and dependencies.
- **Preserve existing Open Questions** when resolving them (strikethrough + append resolution).

## Worked example: CSM quorum loss TSG family

This skill was applied to `tsgs/csm-quorum-loss/`:

**Phase 1 — Gap inventory:**

| TSG | Tool needed | Existing ability? |
|---|---|---|
| identify-offline-csms | XDS role list + ping | Missing |
| check-deployment-status | XDS upgrade state | Missing |
| identify-node-state | Kusto query | ✅ `kusto-query` |
| recover-node-hi | XDS quarantine + Geneva Actions | Missing |
| recover-node-ofr | XDS repair status | Missing |
| escalate-gdco-tickets | Geneva Action (GDCOChangeSeverity) | Missing |

**Phase 3 — Discovery results:**

- Found `xds_client` package in `.venv` (27 API classes, Swagger-generated). Key APIs: `RoleInstancesApi`, `UpgradeStateApi`, `ManagementRoleApi`. 200+ notebook imports found.
- Found `xportal.acis` module in `.venv` (3 functions: `execute`, `submit`, `get_result`). Dozens of notebook uses.

**Phase 4 — Created coding abilities:**

- `xds-api-call`: role instances, upgrade state, management role, XTable. All examples from validated notebooks.
- `geneva-action-call`: ACIS operations. Config/scrubber/partition examples validated from notebooks. Node recovery and GDCO operations flagged as "documented but not validated" — no notebook calls `acis.execute()` directly for those operations.

**Phase 5 — Updated 5 TSGs:**

- Updated `CODING_ABILITY_DEPENDENCY` in all 6 TSGs with specific API methods.
- Resolved 3 Open Questions (XDS API availability, Geneva Action polling, GDCOChangeSeverity API).
- Updated `AUTOMATABLE` assessments from "No/None" to "Yes" or "Partially" where APIs were confirmed.

## Output expectations

When finished, summarize:

- TSG folder analyzed and number of TSGs reviewed.
- Gap table: TSG → tool needed → coding ability (existing/new/still missing).
- Coding abilities created or updated (with file paths).
- TSGs updated (which files, what changed in Automation Notes).
- Resolved Open Questions (list).
- Remaining gaps that could not be closed (with reasons).
- Automation readiness per TSG (fully/partially/manual).
