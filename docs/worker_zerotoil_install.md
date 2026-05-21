# Worker-Side: ZeroToil Package Installation

## Overview

When a notebook job includes the `ZEROTOIL_PACKAGE_VERSION` parameter in
`InputParametersJson`, the TryExecute worker must install the matching
`zerotoil` package from the ADO PyPI feed before executing the notebook.

This replaces the previous blob-storage-based `ZEROTOIL_PACKAGE_ID` flow.

---

## What the Worker Receives

The Service Bus message `InputParametersJson` will contain:

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260413061005",
  "FORCE_REFRESH_NOTEBOOK_CACHE": true
}
```

`ZEROTOIL_PACKAGE_VERSION` is a PEP 440 dev version string like
`0.0.1.dev260413061005`.  Each value is a unique, opaque identifier for a
specific build — not a semantic version.

---

## What the Worker Needs to Do

### 1. Detect the parameter

Check whether `ZEROTOIL_PACKAGE_VERSION` exists in the job's parsed
`InputParametersJson` dict.  If absent, skip — no zerotoil package is
needed for this job.

```python
params = json.loads(message["InputParametersJson"])
zerotoil_version = params.get("ZEROTOIL_PACKAGE_VERSION")
```

### 2. Install from the ADO feed

If the version is present, run `pip install` with the exact version
pinned and the feed URL as the index:

```python
import subprocess

FEED_URL = (
    "https://msazure.pkgs.visualstudio.com"
    "/One/_packaging/Storage-XI-feed/pypi/simple/"
)

if zerotoil_version:
    subprocess.run(
        [
            "pip", "install", "--no-deps",
            f"zerotoil=={zerotoil_version}",
            "--index-url", FEED_URL,
        ],
        check=True,
    )
```

Key flags:
- `--no-deps` — the zerotoil wheel has no declared dependencies (they are
  already present in the worker environment via xportal, xds-client, etc.).
- `--index-url` — points to the private ADO feed.  The worker must have
  credentials configured (see Authentication below).
- `zerotoil==<exact_version>` — pin to the exact version; never install
  the "latest".

### 3. Timing

Install **after** the worker sets up its base environment but **before**
the notebook kernel starts.  The notebook code will `import zerotoil`.

---

## Authentication in the Worker

The worker AKS pods already authenticate to the `Storage-XI-feed` for
other internal packages (xportal, xds-client, xstore, xaiops).  The same
credential mechanism works for zerotoil:

| Environment | Auth Method |
|---|---|
| **AKS worker pod** | `PipAuthenticate` task in the job setup, or `artifacts-keyring` + managed identity |
| **Local dev** | `artifacts-keyring` via `az login` (already configured by `init.cmd`) |

If the worker already runs `pip install --index-url <Storage-XI-feed>` for
other packages, no additional auth setup is needed — just add `zerotoil`
to the same install step.

---

## Pseudocode: Full Integration Point

```python
# In the worker's job-setup phase, after parsing the Service Bus message:

import json
import subprocess

FEED_URL = (
    "https://msazure.pkgs.visualstudio.com"
    "/One/_packaging/Storage-XI-feed/pypi/simple/"
)

def maybe_install_zerotoil(input_parameters_json: str) -> None:
    """Install zerotoil if the job requests it."""
    params = json.loads(input_parameters_json)
    version = params.get("ZEROTOIL_PACKAGE_VERSION")
    if not version:
        return

    print(f"[ZeroToil] Installing zerotoil=={version} from feed …")
    result = subprocess.run(
        [
            "pip", "install", "--no-deps",
            f"zerotoil=={version}",
            "--index-url", FEED_URL,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[ZeroToil] WARNING: pip install failed:\n{result.stderr}")
        raise RuntimeError(f"Failed to install zerotoil=={version}")

    print(f"[ZeroToil] ✔ zerotoil=={version} installed")
```

---

## Rollback / Cleanup

- Each version is independent.  There is no "latest" to worry about.
- If a job fails, the version string in the logs tells you exactly which
  snapshot was used.
- Old versions accumulate in the feed.  They can be cleaned up via the
  ADO Artifacts UI or REST API, but this is not urgent — dev versions
  are tiny (~25 KB each).

---

## Migration Checklist

- [ ] Add `maybe_install_zerotoil()` (or equivalent) to the worker's
      job-setup phase
- [ ] Call it after base environment setup, before notebook kernel start
- [ ] Ensure the worker pod has feed authentication (should already work
      if other internal packages install successfully)
- [ ] Test with: `"ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260413061005"`
      (this version is already published and available in the feed)
