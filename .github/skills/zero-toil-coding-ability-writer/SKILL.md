---
name: zero-toil-coding-ability-writer
description: "Creates or updates a ZeroToil coding ability (a code-generation building block) under coding-abilities/. Produces an ABILITY.md with type-accurate remarks and a compact async code snippet, grounded in real .venv source signatures and existing notebook usage. Optionally generates curated reference examples and assets. USE FOR: create coding ability, update coding ability, coding ability writer, add coding ability, new coding ability, document API for TSG, prepare coding abilities from TSG requirements."
---

# Zero-Toil Coding Ability Writer

This skill creates or updates **ZeroToil coding abilities** — documentation-first code-generation building blocks used by the TSG code writer.

## When to apply this skill

- Creating a new coding ability for a target API/module (e.g., `xportal.kusto.query`, `xportal.icm.get_incident`).
- Updating an existing coding ability with new parameters, return types, or usage patterns.
- Generating curated reference examples by scanning `jupyter-templates/` notebooks.
- Preparing assets (sample outputs, schemas) for a coding ability.

## Inputs to gather (only if missing)

If the user does not supply enough info, ask up to 3 clarifying questions:

1. **Mode + identity**: create a new coding ability vs update an existing one (`coding-abilities/<coding-ability-id>/`)
2. **Target API/module** and the specific call(s) the coding ability demonstrates (e.g., `xportal.kusto.query`, `xportal.icm.get_incident`)
3. **Safety constraints + boundaries** (read-only vs mutating; maximum time range; row limits)

If reference generation is requested and underspecified, ask one additional clarifier:
- Which categories to group by (or accept defaults: by product area / dataset / "incidents vs deployments vs infra vs billing").

Default assumptions if not specified:
- Read-only behavior
- Time-boxed queries (e.g., last 10 minutes / 1 hour)
- Small result sampling (`take N`, `head(N)`)

## Where files go

| Item | Path |
|---|---|
| Coding ability | `coding-abilities/<coding-ability-id>/ABILITY.md` |
| Index | `coding-abilities/README.md` |
| References (optional) | `coding-abilities/<coding-ability-id>/references/` |
| Assets (optional) | `coding-abilities/<coding-ability-id>/assets/` |

`<coding-ability-id>` naming: kebab-case, prefer `system-action` (e.g., `kusto-query-requests`, `icm-search-incidents`).

## ABILITY.md required structure

Every `ABILITY.md` must start with YAML front matter:

```yaml
---
name: <short human-readable name>
description: <one-line short description>
---
```

After the YAML header, the markdown body must contain these sections in order:

1. `# Coding Ability: <coding-ability-id>`
2. `## Description` — one sentence + safety/prerequisite bullets
3. `## Remarks` — key interfaces, function signatures with types, return types, important enums
4. `## Sample Python code` — clean, compact, direct `await` calls with placeholders

### Sample Python code rules

- Keep code clean and compact
- Prefer direct `await` calls (these APIs are async)
- Do **not** include `def main()` / `async def main()` / `if __name__ == "__main__":`
- Do **not** use runtime introspection (`getattr`, `hasattr`, `callable`)
- Use placeholders and safe defaults

### Remarks section (must be grounded in real code)

Source of truth:
- Prefer extracting signatures/types from `.venv/Lib/site-packages/`
- Cross-check existing usage in `jupyter-templates/`
- If `.venv` sources aren't available, state that explicitly

## Authoring workflow

1. **Determine mode**: create (no existing ABILITY.md) or update (minimal edits).
2. **Search** the repo for existing patterns in `jupyter-templates/` and `coding-abilities/`.
3. **Locate** the canonical implementation in `.venv` and extract accurate signatures for Remarks.
4. **Write/update** `ABILITY.md` following the required structure.
5. **Update index** (`coding-abilities/README.md`) only if newly created or metadata changed.
6. **Optional**: generate references and/or assets (only when requested).
7. **Sanity check**: placeholders present, no secrets/PII, read-only by default, Remarks matches actual signatures, every reference cites its source.

## Hard rules (non-negotiable)

- **Never add secrets** (tokens, keys, passwords, SAS) or real customer data; use placeholders.
- **Avoid PII** in examples.
- **Never invent API calls or parameter orders that are not validated.** Every code example must come from:
  1. A real `await` call found in an existing `jupyter-templates/**/*.ipynb` notebook.
  2. The function signature and docstring in `.venv/Lib/site-packages/`.
  3. The official snippets in `jupyter-snippets/public.json`.
- If an operation/parameter is from documentation only (no code source), put it in a "Referenced but not validated" section.
- Do not add or require new dependencies.
- Do not rename/move existing folders.
- Only use `jupyter-templates/` and `.venv` as knowledge sources (not `js-templates/`).
- Keep diffs narrowly scoped.

## Reference generation (when requested)

Source material:
- Scan `jupyter-templates/**/*.ipynb` for real usage patterns
- Check `jupyter-snippets/public.json` for official snippets
- Use `.venv` only for accurate interfaces/types

Validation rules:
- **Every code example must cite its source** — include "Source:" with the repo-relative notebook path.
- Distinguish: **Validated** (real notebook call) vs **API source validated** (.venv signature, no notebook) vs **Documentation-only** (TSG/KB docs only).

Extraction rules:
- Replace environment-specific literals with placeholders
- Keep examples short and safe-by-default (`| take <N>`, bounded time filters)
- Avoid write/control commands

Grouping defaults:
- `incidents`, `deployments`, `infra-health`, `billing-usage`, `generic-patterns`

Reference file layout:
- Multiple small markdown files (e.g., `references/incidents.md`, `references/infra-health.md`)
- Each: short header, 2–6 representative examples, source citations

## Assets (when requested)

- Only create if it adds reviewable value (sample output schema, small CSV with placeholder columns, diagram)
- Never include real outputs with identifiers
- Prefer an `assets/README.md` explaining what's included

## Pipeline context

This skill is typically invoked **before** TSG code generation:

1. `tsg-document-writer` → writes TSG analysis documents, flags automation gaps
2. **This skill** → creates coding abilities for the APIs needed to close those gaps
3. `tsg-code-writer` → generates `.py` modules using coding abilities as building blocks
4. `zerotoil-xjpl-template-publisher` → publishes `.py` modules as `.ipynb` templates
