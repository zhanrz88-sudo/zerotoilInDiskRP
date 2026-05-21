---
name: learn-xds-api-coding-ability
description: "Systematic 5-phase methodology for discovering and documenting an unfamiliar Python API from .venv sources and jupyter-templates usage patterns. Produces a coding ability (ABILITY.md + grouped references) under coding-abilities/. USE FOR: learn API, discover module, document package, create coding ability from source, xds_client, xportal, explore .venv."
---

# Learn XDS API Coding Ability

This skill teaches a systematic methodology for learning an unfamiliar Python API module and producing a production-ready coding ability with grouped reference docs.

It was developed while learning the `xds_client` module and is designed to be reapplied to any package in `.venv/Lib/site-packages/`.

## When to apply this skill

- Creating a coding ability for a module you haven't seen before.
- The target module exists in `.venv/Lib/site-packages/` and/or is used in `jupyter-templates/`.
- You need structured, type-accurate documentation grounded in real source code — not guesses.

## Inputs needed

1. **Target module** — the Python package to learn (e.g., `xds_client`, `xportal.kusto`)
2. **Focus area** (optional) — which sub-APIs or use cases matter most (e.g., "role instance health and upgrade state")
3. **Coding ability ID** (optional) — the kebab-case name for the coding ability folder (e.g., `xds-api-call`)

Default assumptions if not specified:
- Learn all discoverable sub-APIs (breadth-first)
- Read-only usage patterns only
- Group references by API family / functional area

## Hard rules (non-negotiable)

- Never add secrets, tokens, keys, or real customer data; use placeholders.
- Do not invent signatures — every type/method must be grounded in `.venv` source or `jupyter-templates/` usage.
- Do not add new dependencies.
- Keep diffs scoped to the new coding ability folder + index updates only.

## Learning methodology (5 phases)

Follow these phases in order. Each phase builds on the previous.

### Phase 1 — Package discovery

Goal: understand the top-level structure of the target module.

1. **Find the package** in `.venv/Lib/site-packages/<module>/`.
   ```
   Get-ChildItem "<path>" -Directory | Select-Object Name
   Get-ChildItem "<path>" -File | Select-Object Name
   ```
2. **Read `__init__.py`** to see what's exported (API classes, models, helpers).
3. **List sub-packages** (e.g., `api/`, `models/`) and enumerate their files.
4. **Identify the API surface**: each `.py` file in the `api/` folder is typically one API class.

Output: a list of all API classes and model files.

### Phase 2 — Signature extraction

Goal: extract accurate method signatures and return types from the source code.

1. For each API class of interest, **extract all public method names** using regex:
   ```python
   python -c "import re; f=open('<path>'); methods=[m.group(1) for m in re.finditer(r'def (\w+)\(self,', f.read()) if not m.group(1).endswith('_with_http_info')]; f.close(); print('\n'.join(methods))"
   ```
2. **Read the method signatures** in context — focus on:
   - Parameter names and types (from docstrings: `:param <type> <name>:`)
   - Return type (from docstrings: `:return: <type>`)
   - HTTP method + path (from `call_api(path, method)` calls)
   - Required vs optional parameters

3. For key **model classes**, read the `swagger_types` dict at the top of each model file:
   ```python
   swagger_types = { 'field_name': 'type', ... }
   ```
   This gives you the complete schema of request/response objects.

4. **Check for higher-level wrappers** — search for modules like `xstore.common.<name>` that wrap the raw API:
   ```
   Get-ChildItem -Path "<site-packages>/xstore" -Recurse -Filter "<module>*" | Select-Object FullName
   ```

Output: a catalog of methods, their parameters, return types, and model schemas.

### Phase 3 — Usage pattern discovery

Goal: find how real notebook code actually uses the API.

1. **Grep jupyter-templates** for imports:
   ```
   grep_search: "from <module> import|import <module>" in jupyter-templates/**/*.ipynb
   ```
   This shows which API classes are actually used in practice.

2. **Read the most relevant notebooks** — focus on cells that:
   - Import the API class
   - Instantiate and connect the client
   - Call API methods
   - Process the results

3. **Extract the connection pattern** — how does auth/initialization work?
   - For `xds_client`: `api = SomeApi(); await api.api_client.connect_tenant(tenant_name)`
   - For `xportal.*`: usually `await module.some_function(args)`

4. **Note common data processing patterns** — how do templates handle the results?
   - Filtering (e.g., `[r for r in results if r.role_name == "CSM"]`)
   - Converting to DataFrames
   - Extracting specific fields

Output: annotated usage patterns grouped by API family.

### Phase 4 — Cross-reference and validate

Goal: ensure accuracy by cross-referencing sources.

1. **Cross-check signatures**: do the notebook usage patterns match the extracted method signatures?
2. **Verify model fields**: do the fields accessed in notebooks match the `swagger_types` in model files?
3. **Identify read-only vs mutating methods**: label each method as safe (GET) or mutating (POST/PUT/DELETE).
4. **Note any discrepancies or open questions** — if a notebook uses a pattern not in the source, flag it.

Output: validated, cross-referenced API documentation.

### Phase 5 — Produce the coding ability

Goal: write the ABILITY.md and reference documents.

1. **Create `ABILITY.md`** at `coding-abilities/<coding-ability-id>/ABILITY.md` following the standard structure:
   - YAML front matter (`name`, `description`)
   - `## Description` — what the module does, safety notes, prereqs
   - `## Remarks` — connection pattern, API class table, key model schemas (grounded in source)
   - `## Sample Python code` — compact snippet covering the most common use case

2. **Create reference docs** grouped by API family under `coding-abilities/<coding-ability-id>/references/`:
   - One file per logical group (e.g., `role-instances.md`, `upgrade-state.md`)
   - 2–5 examples per file, each with code + "Inspired by" notebook links
   - Clearly label mutating methods with safety warnings

3. **Update indexes**:
   - `coding-abilities/README.md` — add the new coding ability entry
   - `docs/tsg_coding_abilities.md` — add to current coding abilities list

## Reference grouping defaults

If the user doesn't specify grouping, use these defaults:

- Group by **API class / functional area** (e.g., role instances, upgrade state, management role)
- Create a catch-all **`config-and-other-apis.md`** for less-used APIs
- Include a complete API class inventory table in the catch-all file

## Quality checklist

Before finishing, verify:

- [ ] Every method signature matches the `.venv` source code
- [ ] Every model schema matches `swagger_types` in the model file
- [ ] Sample code uses the correct connection pattern (verified from notebooks)
- [ ] No secrets, PII, or real tenant/account names
- [ ] Mutating methods are clearly labeled and gated
- [ ] References cite actual notebook paths (repo-relative)
- [ ] ABILITY.md follows the required section order
- [ ] Indexes are updated

## Worked example: how xds_client was learned

This methodology was applied to produce the `xds-api-call` coding ability:

1. **Package discovery**: Found `xds_client` in `.venv` with `api/` (27 API modules) and `models/` sub-packages. Read `__init__.py` → 26 API classes + hundreds of models exported.

2. **Signature extraction**: Used regex to extract method lists from `RoleInstancesApi` (16 methods), `UpgradeStateApi` (36 methods), `ManagementRoleApi` (33 methods). Read `swagger_types` for `RoleInstance` (9 fields), `UpgradeState` (21 fields), `PingRequestParams` (4 fields), `PingResponse` (8 fields).

3. **Usage pattern discovery**: Grep found 200+ imports across jupyter-templates. Key patterns:
   - Connection: `api = SomeApi(); await api.api_client.connect_tenant(tenant_name)`
   - Role listing: `await role_api.role_instances_get_role_instances()` → filter by `role_name`
   - Ping: `models.PingRequestParams(role_instance_names=[...], request_role_ping=True, ...)`
   - Upgrade state: `await upgrade_api.upgrade_state_get_upgrade_state()` → read `.upgrade_status`, `.current_domain_id`
   - Found higher-level wrapper: `xstore.common.xds.XdsApiClient` for XTable reads.

4. **Cross-reference**: Verified notebook patterns match source signatures. Confirmed `PingResponse.role_status` values from notebook evaluation code. Classified 85%+ of methods as read-only.

5. **Produced**: ABILITY.md with connection pattern, 10-class API table, 4 model schemas, sample code. 4 reference files grouped by: role-instances, upgrade-state, management-role, xtable/xstream/xcompute, config/other. Updated both indexes.

## Output expectations

When finished, summarize:

- What you learned (module name, number of API classes, key findings)
- What you created (coding-ability-id, file paths, reference file count)
- What indexes you updated
- Any open questions or gaps discovered during learning