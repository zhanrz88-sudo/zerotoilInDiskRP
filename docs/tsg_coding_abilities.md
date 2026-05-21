# TSG Coding Abilities (tsg_coding_abilities)

This document defines the **TSG coding abilities** convention used by ZeroToil to provide small, reusable "building block" examples for code generation.

A *coding ability* is not a runnable program. It is a compact reference showing the minimal API calls/patterns needed to accomplish a single task (e.g., "get an ICM incident", "run a Kusto query"). Coding abilities are designed to be embedded into generated code or copied into notebooks.

## Goals

- Provide **stable, minimal snippets** that code generation can reuse.
- Encode **safe-by-default** patterns (read-only unless explicitly required).
- Keep examples **template-like**: placeholders instead of environment-specific values.
- Make coding abilities **discoverable** and **easy to review**.

## Non-goals

- Coding abilities are **not** full workflows or end-to-end automation.
- Coding abilities are **not** responsible for authentication/credential setup.
- Coding abilities are **not** a general cookbook (keep scope tight).

## Location and structure

Coding abilities live under:

- `zero-toil/coding-abilities/`

Conventions:

- One folder per coding ability: `zero-toil/coding-abilities/<coding-ability-id>/`
- Each coding ability folder contains one primary file:
  - `ABILITY.md`
- A coding ability folder may optionally include supporting documentation and assets:
  - `references/` (additional examples, query variants, deeper docs)
  - `assets/` (images, mock data, sample outputs, etc.)
- No `owners.txt` is required under `zero-toil/coding-abilities/`.

Recommended `coding-ability-id` naming:

- Kebab-case, verb-noun or system-action style, e.g. `icm-get-incident`, `kusto-query`, `dgrep-query`, `mdm-query`.

## ABILITY.md format

Each `ABILITY.md` must start with a YAML front matter header block containing the coding ability's display metadata:

```yaml
---
name: <short human-readable name>
description: <one-line short description>
---
```

After the YAML header, the markdown body should contain these sections:

- **Description**: detailed description (what it does, safety notes, prerequisites)
- **Remarks**: interface signatures, parameter types, return types, and key helper methods (sourced from the runtime modules in `zero-toil/.venv`)
- **Sample Python code**: compact snippet demonstrating API usage

### Sample code rules

The sample code is for *showcase* and code generation reference.

- Keep it **clean and compact**.
- Avoid runtime introspection patterns (e.g., `getattr(...)`, `hasattr(...)`, `callable(...)`). Prefer direct calls that match the standard XPortal runtime.
- Do **not** include module-level docstrings inside code blocks.
- Do **not** include `def main()` / `async def main()` wrappers.
- Do **not** include `if __name__ == "__main__":` runners.
- Prefer `await` directly in the snippet (these APIs are async).
  - Assumption: the snippet is pasted into a notebook / async context where `await` is valid.
- Use placeholders such as `<incident_id>`, `<cluster>`, `<database>`, `<namespace>`, `<metric>`.
- Keep snippets **read-only by default**. If a coding ability must mutate state, call that out explicitly and include a safety guard.

## How code generation should use coding abilities

Generated code can:

- Copy the snippet and replace placeholders with variables derived from the TSG.
- Inline additional guardrails (time-range limits, `take N`, narrow filters).
- Add surrounding orchestration (parameter parsing, retries/backoff) outside the coding ability.

Coding abilities should remain:

- Minimal (only the essential imports/calls)
- Independent (avoid depending on other coding abilities)
- Stable (avoid frequent renames/moves)

## Adding a new coding ability

1. Create `zero-toil/coding-abilities/<coding-ability-id>/ABILITY.md`.
2. Keep the sample snippet short and safe.
3. Add the coding ability to the index in `zero-toil/coding-abilities/README.md`.

Optional: add supporting materials under `references/` or `assets/` if the coding ability benefits from additional examples (e.g., query variants, sample result formats, mock data for testing).

## Current coding abilities

- `icm-get-incident`: fetch incident entity from ICM, update severity/tags/description, mitigate, resolve, transfer
- `kusto-query`: run KQL against a Kusto cluster
- `dgrep-query`: query DGrep logs
- `mdm-query`: query MDM metrics via KQL-m
- `ado-build-query`: query Azure DevOps build pipelines, releases, and commits via `xportal.ado` and Kusto
- `xds-api-call`: call XDS REST APIs (role instances, upgrade state, management role, XTable, etc.) via `xds_client`
- `geneva-action-call`: execute Geneva Actions (ACIS) via `xportal.acis` — node recovery, config changes, GDCO tickets
