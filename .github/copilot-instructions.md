# GitHub Copilot instructions (zerotoilfordiskRP)

This repo is the **standalone ZeroToil framework for DiskRP** on-call automation. It contains TSG implementations, coding abilities, and backend job submission tooling.

Copilot should optimize for **safe, minimal, reviewable changes** that fit the existing structure.

## Non‑negotiables

- **Never add secrets** (tokens, keys, SAS, passwords), and never paste real customer data.
- **Avoid PII** in examples and logs. Use placeholders like `<tenant>`, `<subscriptionId>`, `<account>`.
- **Do not “clean up” unrelated code**. Keep diffs narrowly scoped to the request.
- **Preserve folder structure**. Do not rename existing directories.
- If adding a new template/notebook, ensure there is a clear **owner** and placement under the right product folder.

## Repository structure (where things go)

- `zerotoil/`: The `zerotoil` Python package source.
  - `zerotoil/core/framework.py`: TsgBase class and execution engine.
  - `zerotoil/tsgs/`: Executable TSG implementations (Python).
- `coding-abilities/`: API usage patterns, gotchas, and source references (one folder per ability with `ABILITY.md`).
- `scripts/`: Build, publish, and job submission scripts.
- `tests/`: Unit tests (pytest).
- `tsgs/`: TSG analysis documents (markdown decompositions for code generation).
- `docs/`: Framework documentation, change notes, guides.
- `temp-workspace/`: **Git-ignored** scratch folder for temporary `.ipynb` files.
- `.venv/`: **Git-ignored** Python virtual environment. Activate with `& .venv\Scripts\Activate.ps1`.

## Knowledge persistence (critical rule)

**Always persist knowledge gained from user input, investigation, and debugging into durable artifacts** so future sessions can reference it without re-discovery:

- **Skills** (`.github/skills/`): Reusable workflows and methodologies (e.g., how to map PowerShell cmdlets to Python APIs, how to run end-to-end TSG automation).
- **Agent definitions** (`.github/agents/`): Hard rules and patterns sub-agents (like `tsg-code-writer`, `tsg-document-writer`) must follow. When a new mandatory pattern emerges (e.g., dry-run guards, retry helpers), add it here so the sub-agent's generated output enforces it automatically.
- **Coding abilities** (`coding-abilities/`): API usage patterns, code snippets, gotchas, and source code references (include full ADO URLs).
- **Change notes** (`docs/change-notes/`): Why a change was made, what was validated, what remains open.
- **TSG docs** (`tsgs/`): Decomposed TSG steps, automation assessments, open questions.

When the user shares information (e.g., source code locations, API behavior, tenant quirks, incident patterns), write it down in the appropriate artifact — do not rely on conversation memory alone.

## Always read existing coding abilities before coding fallbacks (critical rule)

Before adding any helper, retry, fallback, or "best-effort" path that touches storage accounts, tenants, XDS, DGrep, Kusto, ICM, Geneva Actions, MDM, or any other XStore API:

1. **List `coding-abilities/`** and read every `ABILITY.md` whose name even loosely relates to the API you are about to use.
2. The ability docs already capture hard constraints, environment differences, and forbidden patterns. Examples that have caused real bugs when ignored:
   - **SRP/RSRP tenants are NOT storage tenants.** `xds.search_log("RSRP...", ...)` returns HTTP 500 / `EndpointNotFoundException`. Never substitute an SRP tenant for a storage tenant in any XDS call. (Documented in `storage-account-tenant-metadata` and `xds-log-search`.)
   - **Backend `xstore.get_account` differs from local `.venv`.** The XJupyterLite image ships an older version that only consults the XDS metadata service; the local `.venv` falls back to Kusto via XPortal. The fix for missing PreProd accounts on the backend is to upgrade the image, not to invent client-side fallbacks.
3. If the existing ability is incomplete, **update the ability** with the new finding before you write code that depends on it.

Skipping this step has produced harmful workarounds (e.g., passing an RSRP tenant to `xds.search_log`). Treat the coding-abilities scan as mandatory, not optional.

## Backend job submission rules

When you submit a `zerotoil` job to the XJupyterLite backend (via `run-zerotoil-job-in-backend` skill or `scripts/run_zerotoil_job.py`):

1. **Surface the report URL immediately** in your reply, *before* polling for results. The user wants to open the report in parallel with your tracking. Format:
   ```
   Report URL: https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=<job_id>_temp_run.html
   Job ID:     <job_id>
   Package:    zerotoil==<version>
   ```
   Never wait until the job finishes to show the URL — show it the moment the submission API returns the job ID.

2. **Default to dry-run for live incidents.** If running a TSG against a real incident ID, construct the notebook with `tsg = <TsgName>(dry_run=True)` so ICM writes/transfers/mitigations are skipped. Only run with `dry_run=False` after a dry-run report has been reviewed and looks correct.

3. **Record the job in the change note.** When a backend run validates an active change, append a row to the change note's `## Assets` section with date, job ID, `dry_run` flag, incident ID, and report URL. This keeps a durable trail of which backend runs validated which code change. Example:
   ```
   - 2026-04-28 · `b8d607ee-...` · dry_run=True · incident=786460728 · [report](https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=b8d607ee-..._temp_run.html)
   ```

## When unsure

- Choose the simplest change that satisfies the request.
- Ask a small number of clarifying questions when behavior or placement is ambiguous.
