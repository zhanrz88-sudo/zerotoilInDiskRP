# ZeroToil Package Upload Specification

## Overview

Publish the zerotoil Python package to an **Azure DevOps PyPI feed** so that
XJupyterLite's TryExecute worker can `pip install` it at notebook execution time.

Each build produces a **unique dev version** — there is no linear version
history.  Every build is an independent, disposable debug snapshot identified
solely by its version string.

## Distribution Channel

| Field | Value |
|---|---|
| Feed | [Storage-XI-feed](https://msazure.visualstudio.com/One/_artifacts/feed/Storage-XI-feed) |
| Feed URL (pip) | `https://msazure.pkgs.visualstudio.com/One/_packaging/Storage-XI-feed/pypi/simple/` |
| Feed URL (twine) | `https://msazure.pkgs.visualstudio.com/One/_packaging/Storage-XI-feed/pypi/upload/` |
| Auth | `artifacts-keyring` (auto-prompts via Azure DevOps credential provider) |

## Version Format

Each build stamps a unique [PEP 440](https://peps.python.org/pep-0440/) dev version:

```
0.0.1.dev<YYMMDDHHMMSS>
```

Example: `0.0.1.dev260413061005`

- `YYMMDDHHMMSS`: UTC timestamp (2-digit year, 12 digits total)
- Second-level precision is unique enough for single-developer debug builds
- If a collision occurs, twine rejects the duplicate and you just re-run

These versions are **not ordered semantically**.  Each one is an opaque
identifier for a specific code snapshot.

## How the Consumer Uses the Version

After publishing, pass the version string as a parameter to the notebook job:

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260413061005"
}
```

The TryExecute worker should:
1. Read `ZEROTOIL_PACKAGE_VERSION` from `InputParametersJson`
2. Run `pip install zerotoil==<version> --index-url <feed-url>`
3. The notebook can then `import zerotoil`

## Local Build & Publish

```bash
cd zero-toil
pip install build twine keyring artifacts-keyring

# Build + publish (one command)
python scripts/build_and_upload_package.py

# Dry-run (build only, no publish)
python scripts/build_and_upload_package.py --dry-run
```

## Build, Publish & Run (all-in-one)

```bash
python scripts/run_zerotoil_job.py

# With options
python scripts/run_zerotoil_job.py --notebook Xstore/ZeroToil/MyTsg.ipynb --environment test
python scripts/run_zerotoil_job.py --dry-run
python scripts/run_zerotoil_job.py --params '{"INCIDENT_ID":"12345"}'
```

## Dependencies

```
pip install build twine keyring artifacts-keyring
```

---

## Legacy: Blob Storage Upload (deprecated)

> The blob-based upload to `xportals.blob.core.windows.net` / container
> `xjupyterlite-zerotoil` is superseded by the ADO feed approach above.
> The blob path required cross-tenant credentials that are not available
> to most developers locally.  The feed approach uses the same
> `artifacts-keyring` credential provider that the rest of the repo
> already depends on.
