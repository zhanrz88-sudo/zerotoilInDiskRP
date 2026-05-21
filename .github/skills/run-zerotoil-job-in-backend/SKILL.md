---
name: run-zerotoil-job-in-backend
description: "Build the zerotoil package, publish it to the ADO PyPI feed, and submit a notebook job to the XJupyterLite backend via XPortal API. Supports local notebook uploads (temporary runs) and existing template paths. USE FOR: run zerotoil job, submit notebook job, test zerotoil code, build and publish zerotoil, run notebook in backend, submit XJPL job, run local notebook, temporary run, test TSG in backend, dry run zerotoil."
---

# Run ZeroToil Job in Backend

This skill builds the `zerotoil` Python package, publishes it to the ADO PyPI feed, and submits a notebook job to the XJupyterLite (XJPL) backend so the remote worker can `pip install zerotoil==<version>` and execute the notebook.

## When to apply this skill

- When the user wants to **test zerotoil code** in the backend environment.
- When the user asks to **run a notebook** on XJupyterLite.
- When the user asks to **submit a job**, **run in backend**, or **test a TSG remotely**.
- When the user wants to **build and publish** the zerotoil package (with `--dry-run`).
- After making changes to `zerotoil/` code and wanting to verify it works remotely.

## Key scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `run_zerotoil_job.py` | `scripts/run_zerotoil_job.py` | End-to-end: build → publish → submit job |
| `build_and_upload_package.py` | `scripts/build_and_upload_package.py` | Build wheel + publish to ADO feed only || `fetch_job_report.py` | `scripts/fetch_job_report.py` | Fetch job status + execution results via XPortal API |
## Prerequisites

Install the required packages (one-time setup):

```bash
pip install build twine keyring artifacts-keyring
```

Additional requirements:
- `az login` — needed for ADO feed authentication via `artifacts-keyring`.
- `xportal` package installed — provides the XPortal SDK for job submission (installed via `init.cmd`).

## How it works

### Pipeline overview

1. **Generate version** — A unique PEP 440 dev version: `0.0.1.dev<YYMMDDHHmmSS>`.
2. **Build wheel** — Stamps the version into `pyproject.toml`, builds a `.whl`, then resets `pyproject.toml` to `0.0.0`.
3. **Publish to feed** — Uploads the wheel to the `Storage-XI-feed` ADO PyPI feed via `twine`.
4. **Submit job** — Calls the XPortal API with `ZEROTOIL_PACKAGE_VERSION` so the backend worker installs the exact version.

### Two submission modes

| Mode | Flag | How it works |
|------|------|-------------|
| **Local notebook (temporary run)** | `--local-notebook path/to/file.ipynb` | Uploads a local `.ipynb` file as a temporary run. The backend worker downloads and executes it. |
| **Existing template** | `--notebook Xstore/path/to/template.ipynb` | Runs an already-published template on XJupyterLite. |

### Authentication

The XPortal SDK requires authentication. On first run (or when cookies expire), the script prompts:

```
🔐 Automatic browser capture unavailable.
   Please open this URL and log in:
   https://xportal-aad.trafficmanager.net/tenantcatalog

   After logging in, open F12 → Application → Cookies
   Copy all cookie name=value pairs (or use Console: document.cookie)

   Paste cookie here:
```

Paste the `.AspNet.Cookies=...` value from the browser to authenticate.

## Step-by-step workflow

### Step 1 — Prepare the notebook

If running a local notebook, create an `.ipynb` file with the code to test. The notebook must be valid Jupyter format.

**Store temporary notebooks in `temp-workspace/`** — this folder is git-ignored and reserved for scratch/temporary `.ipynb` files used for job submissions. Never place temporary notebooks in `scripts/` or other tracked directories.

**Minimal test notebook example** (to verify zerotoil imports):

```json
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import zerotoil.core\n",
    "import zerotoil.tsgs\n",
    "print('import zerotoil successfully')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": { "display_name": "Python 3", "language": "python", "name": "python3" },
  "language_info": { "name": "python", "version": "3.10.0" }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

Save it as an `.ipynb` file in the temp workspace (e.g., `temp-workspace/test_import_zerotoil.ipynb`).

### Step 2 — Run the script

Navigate to the `` directory and run:

```bash
cd d:\gitroot\XScript-Templates\zero-toil
python scripts/run_zerotoil_job.py --local-notebook temp-workspace/test_import_zerotoil.ipynb --environment test -o
```

The script will:
1. Build the wheel and print `✔ zerotoil-0.0.1.dev<timestamp>-py3-none-any.whl`
2. Publish to the ADO feed and print `✔ Published: zerotoil==<version>`
3. Submit the job and print the **Job ID** and **Report URL**
4. With `-o`, wait 20 seconds then open the report in the browser

### Step 3 — Fetch execution results

After submission, use `fetch_job_report.py` to check job status and retrieve the execution output **programmatically** (without opening a browser):

```bash
cd d:\gitroot\XScript-Templates\zero-toil
python scripts/fetch_job_report.py <job_id> --temp-run
```

For template runs (not temporary):
```bash
python scripts/fetch_job_report.py <job_id>
```

The script does the following:

1. **Fetches job status** via `GET /api/v1/XJupyterlite/GetAKSJobResult?jobId=<job_id>` — returns a JSON object with `Status` (`Success`, `Fail`, `Pending`, `FailedJobSubmission`), timing info, parameters, and cluster details.
2. **Fetches the HTML report** via `GET /xjupyterlitereport?path=<blob_path>` — returns the full rendered notebook HTML. The script extracts cell outputs from `<pre>` tags and prints them.
3. **Fetches the original notebook blob** via `GET /api/v1/XJupyterlite/LoadPickleObj?id=<blob_id>` — returns the raw notebook JSON that was uploaded.

**Example output:**
```
Fetching job status for bb96ac1a-63fd-4e34-9ce9-bf8a4ad8aa9c ...
  Job result: {'Status': 'Success', 'StartTime': '...', 'EndTime': '...', ...}

  [Report page (raw)] /xjupyterlitereport?path=bb96ac1a-..._temp_run.html
    ✔ Got 651029 chars
    Output cells found:
      [0] import zerotoil.core
          import zerotoil.tsgs
          print('import zerotoil successfully')
      [1] import zerotoil successfully
```

**Key fields in the job result JSON:**

| Field | Description |
|-------|-------------|
| `Status` | `Success`, `Fail`, `Pending`, or `FailedJobSubmission` |
| `StartTime` / `EndTime` | Execution timestamps (UTC) |
| `Reason` | Error reason if status is `Fail` |
| `Environment` | `Test`, `Stage`, or production |
| `ClusterName` | Which cluster ran the job |
| `InputParametersJsonString` | The parameters passed to the job |

### Alternative: Check the report in browser

You can also open the report URL directly in a browser. The URL format is:

```
https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=<job_id>_temp_run.html
```

For template runs:
```
https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=<job_id>_/<template_path>.html
```

Pass `-o` to `run_zerotoil_job.py` to open the report automatically after submission.

## CLI reference

```
python scripts/run_zerotoil_job.py [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--local-notebook PATH` | _(none)_ | Path to a local `.ipynb` file to upload and run as a temporary notebook. |
| `--notebook PATH` | `Xstore/Developer/zifanni/zt-test.ipynb` | Template path on XJupyterLite (used when `--local-notebook` is not set). |
| `--environment` | `test` | Target environment: `test`, `stage`, or `prod`. |
| `--version VERSION` | _(none)_ | Skip build/publish and reuse an already-published version. |
| `--dry-run` | _(off)_ | Build and publish the package but do NOT submit a job. |
| `-o` / `--open` | _(off)_ | Open the report in the browser after submission (waits 20s). |
| `--log worker\|job` | _(none)_ | Stream kubectl logs for the worker or job pod (requires kubectl access). |
| `--params JSON` | `{}` | Extra parameters as a JSON string, e.g. `'{"TENANT":"foo"}'`. |
| `--usage` | — | Show common usage examples and exit. |

## Common usage examples

```bash
# 1. Build + publish + run a local notebook (most common for testing)
python scripts/run_zerotoil_job.py \
    --local-notebook path/to/my_notebook.ipynb -o

# 2. Reuse an already-published version (skip build/publish)
python scripts/run_zerotoil_job.py \
    --local-notebook path/to/my_notebook.ipynb \
    --version 0.0.1.dev260415033907 -o

# 3. Run an existing template on XJupyterLite
python scripts/run_zerotoil_job.py \
    --notebook Xstore/Developer/zifanni/zt-test.ipynb -o

# 4. Build + publish only (no job submission)
python scripts/run_zerotoil_job.py --dry-run

# 5. Run with extra parameters
python scripts/run_zerotoil_job.py \
    --local-notebook my_notebook.ipynb \
    --params '{"TENANT":"my-tenant","ICM_ID":"12345"}' -o

# 6. Run and stream job pod logs (requires kubectl)
python scripts/run_zerotoil_job.py \
    --local-notebook my_notebook.ipynb --log job

# 7. Fetch execution results for a completed job (temp run)
python scripts/fetch_job_report.py <job_id> --temp-run

# 8. Fetch execution results for a template run
python scripts/fetch_job_report.py <job_id>
```

## Running a TSG for a specific incident

This is the most common use case: run a zerotoil TSG against a live ICM incident in the backend.

### Available TSGs

| TSG class | Module | Typical incident title pattern |
|-----------|--------|-------------------------------|
| `FailoverPendingTransaction` | `zerotoil.tsgs.failover_pending_transaction` | `[FailoverPendingTransaction] ... stuck on ...Stuck.... in RSRP...` |
| `Csm2FailuresFromQuorumLoss` | `zerotoil.tsgs.csm_quorum_loss` | `CSM 2 Failures Away from Quorum Loss ...` |
| `EscalateGdcoTickets` | `zerotoil.tsgs.escalate_gdco_tickets` | GDCO ticket escalation |
| `MitigateXnamespaceDirectorystatisticsBlock` | `zerotoil.tsgs.mitigate_xnamespace_directorystatistics_block` | XNamespace DirectoryStatistics block |
| `XinvestigatorProcessCrash` | `zerotoil.tsgs.xinvestigator_process_crash` | XInvestigator process crash |

### Step-by-step: Run a TSG for an incident

**1. Create the notebook** in `temp-workspace/`:

The notebook needs a single code cell with this pattern:

```python
from zerotoil.tsgs.<module_name> import <TsgClassName>

incident_id = "<incident_id>"
tsg = <TsgClassName>()
await tsg.run_for_incident(str(incident_id))
```

**Example** — FailoverPendingTransaction for incident 782424523:

```json
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from zerotoil.tsgs.failover_pending_transaction import FailoverPendingTransaction\n",
    "\n",
    "incident_id = \"782424523\"\n",
    "tsg = FailoverPendingTransaction()\n",
    "await tsg.run_for_incident(str(incident_id))"
   ]
  }
 ],
 "metadata": {
  "kernelspec": { "display_name": "Python 3", "language": "python", "name": "python3" },
  "language_info": { "name": "python", "version": "3.10.0" }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

Save as e.g. `temp-workspace/run_failover_782424523.ipynb`.

**2. Submit the job:**

```bash
cd d:\gitroot\XScript-Templates\zero-toil
python scripts/run_zerotoil_job.py \
    --local-notebook temp-workspace/run_failover_782424523.ipynb \
    --environment test
```

**3. Fetch execution results:**

```bash
python scripts/fetch_job_report.py <job_id> --temp-run
```

### How `run_for_incident` works

`TsgBase.run_for_incident(incident_id)` does:
1. Fetches the ICM incident via `icm.get_incident(incident_id, should_get_description=True)`
2. Calls `_extract_input_from_incident()` to parse the incident title/description into a typed `TsgInput` (e.g. tenant name, start time, stuck stage)
3. Calls `_run(tsg_input)` which executes the TSG steps (DGrep queries, XDS log searches, ICM updates)
4. Returns a typed `TsgOutput` with the results

Each TSG class defines its own `_extract_input_from_incident()` to parse its specific incident format — no manual input construction needed.

### Quick-reference: notebook cell templates

**FailoverPendingTransaction:**
```python
from zerotoil.tsgs.failover_pending_transaction import FailoverPendingTransaction
tsg = FailoverPendingTransaction()
await tsg.run_for_incident("<INCIDENT_ID>")
```

**Csm2FailuresFromQuorumLoss:**
```python
from zerotoil.tsgs.csm_quorum_loss import Csm2FailuresFromQuorumLoss
tsg = Csm2FailuresFromQuorumLoss()
await tsg.run_for_incident("<INCIDENT_ID>")
```

**EscalateGdcoTickets:**
```python
from zerotoil.tsgs.escalate_gdco_tickets import EscalateGdcoTickets
tsg = EscalateGdcoTickets()
await tsg.run_for_incident("<INCIDENT_ID>")
```

**MitigateXnamespaceDirectorystatisticsBlock:**
```python
from zerotoil.tsgs.mitigate_xnamespace_directorystatistics_block import MitigateXnamespaceDirectorystatisticsBlock
tsg = MitigateXnamespaceDirectorystatisticsBlock()
await tsg.run_for_incident("<INCIDENT_ID>")
```

**XinvestigatorProcessCrash:**
```python
from zerotoil.tsgs.xinvestigator_process_crash import XinvestigatorProcessCrash
tsg = XinvestigatorProcessCrash()
await tsg.run_for_incident("<INCIDENT_ID>")
```

## Build-only mode

To build and publish the package without submitting a job, use `build_and_upload_package.py` directly:

```bash
python scripts/build_and_upload_package.py           # Build + publish
python scripts/build_and_upload_package.py --dry-run  # Build only, skip publish
```

This is useful when you just need the version string to pass to another system.

## Hard rules (non-negotiable)

- **Always run from ``** — the scripts use relative paths based on `scripts/`.
- **Never hardcode versions** — each build generates a unique timestamp-based version. Use `--version` only to reuse a previously published version.
- **Do not edit `pyproject.toml` version manually** — the build script stamps and resets it automatically. The version in git should always be `0.0.0`.
- **Local notebooks must be `.ipynb`** — the script validates the file extension.
- **Store temporary notebooks in `temp-workspace/`** — this folder is git-ignored. Never commit scratch notebooks to `scripts/` or other tracked directories.
- **Use `test` environment for development** — only use `stage` or `prod` for validated code.
- **Authentication cookies are session-scoped** — they expire and need to be re-entered when prompted.
- **🚨 Always show the user the report URL immediately after submitting** — the moment the script prints `Job submitted. Job ID: <id>` and the report URL, surface that URL in your reply *before* fetching results. The user wants to be able to open the report in parallel with you, not wait for you to finish polling. Format:
  ```
  Report URL: https://xportal-aad.trafficmanager.net/xjupyterlitereport?path=<job_id>_temp_run.html
  Job ID:     <job_id>
  Package:    zerotoil==<version>
  ```
- **Always test with `dry_run=True` first** when running a TSG against a real incident. Build the notebook with `tsg = <TsgName>(dry_run=True)` so ICM writes/transfers/mitigations are skipped while real DGrep/XDS/Kusto reads still run. Only switch to `dry_run=False` after the dry-run report looks correct.
- **Record every job submission in the change note** — when a backend run is part of an active change, append a row to the change note's `## Assets` section: `<date> · <job_id> · dry_run=<bool> · incident=<id> · <report_url>`. This keeps a durable trail of which backend runs validated which code change.

## XPortal API reference

The scripts communicate with XPortal via `xportal.utils.rest_helper.RestHelper`. The base endpoint is returned by `xportal.utils.get_endpoint()` (for local dev: `https://xportal-aad.trafficmanager.net`).

| API | Method | Purpose |
|-----|--------|---------|
| `/api/v1/XJupyterlite/SubmitAKSJob` | POST | Submit a notebook job |
| `/api/v1/XJupyterlite/GetAKSJobResult?jobId=<id>` | GET | Get job status and metadata |
| `/api/v1/XJupyterlite/SavePickleObj?storageId=<id>` | POST | Upload a blob (notebook content) |
| `/api/v1/XJupyterlite/LoadPickleObj?id=<id>` | GET | Download a blob by ID |
| `/xjupyterlitereport?path=<blob>.html` | GET | Fetch the rendered HTML report |

**Report blob naming:**
- Temporary runs: `<job_id>_temp_run.html`
- Template runs: `<job_id>_/<template_path>.html`

**Authentication** is handled automatically by `RestHelper` — it injects cookies/tokens from the xportal auth flow.

## Troubleshooting

| Problem | Action |
|---------|--------|
| `No module named build` | Run `pip install build twine keyring artifacts-keyring`. |
| `twine upload` fails with 401 | Run `az login` to refresh ADO credentials. |
| Cookie prompt appears | Open the URL shown, log in, copy cookies from F12 → Application → Cookies, paste at the prompt. |
| `Notebook not found` error | Check the `--local-notebook` path is correct and the file exists. |
| Report page is blank | The job may still be running. Wait and refresh. Check the execution time — backend jobs need time to install dependencies and run. |
| Want to rerun without rebuilding | Use `--version <previous_version>` to skip the build/publish steps. |
| Job status is `Pending` | The job is still queued or running. Wait and re-run `fetch_job_report.py`. |
| Job status is `Fail` | Check the `Reason` field in the job result JSON. Common causes: import errors, missing dependencies, or runtime exceptions. |
| Job fails with `NonNotebookException` | **Most common cause**: the `ZEROTOIL_PACKAGE_VERSION` parameter triggers `pip install zerotoil==<version>` on the worker, and the install crashes (dependency conflicts with the worker image). **Fix**: If the notebook does NOT need zerotoil imports (e.g., it only uses `xportal` APIs like `acis.execute`), submit the job **without** the `ZEROTOIL_PACKAGE_VERSION` parameter. Do this by calling the XPortal `SubmitAKSJob` API directly instead of using `run_zerotoil_job.py`. See the "Direct submission without zerotoil" section below. |
| `NonNotebookException` even for simple notebooks | If even `print('hello')` fails, the issue is definitely the zerotoil pip install, not your code. Omit `ZEROTOIL_PACKAGE_VERSION` from `InputParametersJson`. |

## Pipeline context

This skill is typically used in the following workflow:

1. **Develop** — Write or edit code under `zerotoil/` (TSGs, framework, etc.).
2. **Unit test locally** — Run `pytest` via the `zero-toil-unit-test` skill.
3. **Publish notebooks** — Convert `.py` modules to `.ipynb` via the `zerotoil-xjpl-template-publisher` skill.
4. **Test in backend** — Use **this skill** to submit a job and verify the code runs correctly in the remote XJPL environment.
5. **Create PR** — Submit changes via the `zero-toil-create-update-pull-request` skill.

## Direct submission without zerotoil

When a notebook only uses built-in `xportal` APIs (e.g., `acis.execute`, `kusto.query`) and does NOT need the `zerotoil` package, submit the job **without** `ZEROTOIL_PACKAGE_VERSION` to avoid the pip install that causes `NonNotebookException`.

**Root cause discovered 2026-05-19**: The backend worker's `pip install zerotoil==<version>` crashes with `NonNotebookException` due to dependency conflicts between the zerotoil package (e.g., `selenium`, `aiohttp`, `pydantic` version pins) and the pre-installed packages in the worker Docker image (`xaiops.azurecr.io/python-client-image:2.0.712.0`). The crash happens before any notebook code executes, producing zero output cells.

**Diagnosis checklist** (follow this when you see `NonNotebookException`):
1. Check if the notebook actually imports `zerotoil.*`. If not → submit without the package.
2. If the notebook DOES need zerotoil, try a `print('hello')` notebook with the same version to confirm it's the pip install causing the crash.
3. If hello also fails → the zerotoil package has a dependency conflict with the current worker image. Try rebuilding with relaxed version pins.

**Python snippet for direct submission** (no zerotoil package):

```python
import asyncio, json, datetime
from xportal.utils.rest_helper import RestHelper
from xportal.utils import get_endpoint
from urllib.parse import urljoin
from pathlib import Path

async def submit_without_zerotoil(notebook_path: str, environment: str = "Prod"):
    endpoint = get_endpoint()
    body = {
        "Script": "_temp_run",
        "InputParametersJson": json.dumps({"FORCE_REFRESH_NOTEBOOK_CACHE": True}),
        "SubmittedBy": "ZeroToilLocalRun",
        "SubmitTime": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "Environment": environment,
    }
    response = await RestHelper.fetch_post(
        urljoin(endpoint, "/api/v1/XJupyterlite/SubmitAKSJob"),
        json.dumps(body),
    )
    job_id = response["IncidentDiagnosticItemId"]

    blob_id = f"{job_id}_temp_run"
    notebook_content = Path(notebook_path).read_bytes()
    await RestHelper.fetch_post(
        urljoin(endpoint, f"/api/v1/XJupyterlite/SavePickleObj?storageId={blob_id}"),
        notebook_content,
        content_type="application/octet-stream",
    )
    report_url = f"https://xportal-aad.trafficmanager.net/xjupyterlitereport?path={blob_id}.html"
    print(f"Job ID: {job_id}")
    print(f"Report: {report_url}")
    return job_id

asyncio.run(submit_without_zerotoil("temp-workspace/my_notebook.ipynb"))
```

**Validated 2026-05-19**: GetStorageAccount notebook submitted without `ZEROTOIL_PACKAGE_VERSION` → Status: `Success`. Same notebook with the param → `NonNotebookException`.
