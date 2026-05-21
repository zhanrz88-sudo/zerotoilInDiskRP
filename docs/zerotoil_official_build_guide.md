# ZeroToil: Publishing Official Packages

## Overview

The zerotoil repo publishes **two** packages to the same ADO feed
(`Storage-XI-feed`):

| Package | Purpose | Who can publish | Consumed by |
|---|---|---|---|
| `zerotoil` | Dev / test builds | Any developer | Test, Stage |
| `zerotoil-official` | Production builds | **Official CI pipeline only** | **Prod** (and Test/Stage opt-in) |

Both packages share the same source code and provide the same importable
module (`import zerotoil`).  The only difference is the **package name**
in `pyproject.toml` / `setup.py`.

---

## Repository Structure

```
zerotoil/
├── zerotoil/              # importable module (same for both packages)
│   ├── __init__.py
│   ├── tsg.py
│   └── ...
├── pyproject.toml         # default: name = "zerotoil" (dev package)
├── pyproject.official.toml  # override: name = "zerotoil-official"
└── azure-pipelines.yml
```

---

## pyproject.toml Setup

### Dev package (`pyproject.toml`)

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "zerotoil"
dynamic = ["version"]
requires-python = ">=3.8"

[tool.hatch.version]
path = "zerotoil/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["zerotoil"]
```

### Official package (`pyproject.official.toml`)

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "zerotoil-official"
dynamic = ["version"]
requires-python = ">=3.8"

[tool.hatch.version]
path = "zerotoil/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["zerotoil"]
```

> **Key difference**: only `name` changes.  The `packages = ["zerotoil"]`
> stays the same so `import zerotoil` works for both.

---

## Version Format

### Dev version (for `zerotoil` and `zerotoil-official` dev builds)

```
0.0.1.dev<YYMMDDHHMMSS>
```

Example: `0.0.1.dev260428153042`

### Stable version (for `zerotoil-official` release builds)

```
0.0.0.<N>
```

Example: `0.0.0.3`

- `N` is auto-incremented from `LATEST_OFFICIAL_VERSION` by each official build.
- This version is **only published from main branch** builds.
- Prod should pin to stable versions for predictable rollback.

Both versions are stamped in `zerotoil/__init__.py`:

```python
# zerotoil/__init__.py
__version__ = "0.0.1.dev260428153042"
```

The pipeline generates this timestamp automatically.

---

## Pipeline Configuration

### azure-pipelines.yml

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  FEED_URL: 'https://pkgs.dev.azure.com/msazure/One/_packaging/Storage-XI-feed/pypi/upload/'

steps:
  # 1. Generate version from timestamp
  - script: |
      VERSION="0.0.1.dev$(date -u +'%y%m%d%H%M%S')"
      echo "##vso[task.setvariable variable=ZT_VERSION]${VERSION}"
      echo "Version: ${VERSION}"
    displayName: 'Generate version'

  # 2. Stamp version into source
  - script: |
      echo "__version__ = \"$(ZT_VERSION)\"" > zerotoil/__init__.py
    displayName: 'Stamp version'

  # 3. Authenticate to ADO feed
  - task: PipAuthenticate@1
    inputs:
      artifactFeeds: 'One/Storage-XI-feed'

  # 4. Install build tools
  - script: |
      pip install build twine
    displayName: 'Install build tools'

  # 5. Build & publish DEV package (every build)
  - script: |
      python -m build --wheel
      twine upload --repository-url $(FEED_URL) dist/*.whl
    displayName: 'Publish zerotoil (dev)'
    env:
      TWINE_USERNAME: 'build'
      TWINE_PASSWORD: $(System.AccessToken)

  # 6. Clean dist
  - script: rm -rf dist/
    displayName: 'Clean dist'

  # 7. Build & publish OFFICIAL package with dev version (main branch only)
  - script: |
      # Swap to official pyproject.toml
      cp pyproject.official.toml pyproject.toml

      python -m build --wheel
      twine upload --repository-url $(FEED_URL) dist/*.whl
    displayName: 'Publish zerotoil-official (dev version)'
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    env:
      TWINE_USERNAME: 'build'
      TWINE_PASSWORD: $(System.AccessToken)

  # 8. Clean dist
  - script: rm -rf dist/
    displayName: 'Clean dist (before stable)'
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))

  # 9. Build & publish OFFICIAL package with stable version (main branch only)
  #    This publishes zerotoil-official with an incrementing stable version
  #    (e.g. 0.1.0, 0.2.0, ...) so Prod can pin to a release version.
  #    The stable version is derived from the pipeline build counter.
  - script: |
      STABLE_VERSION="0.$(Build.BuildId).0"
      echo "Stable version: ${STABLE_VERSION}"
      echo "__version__ = \"${STABLE_VERSION}\"" > zerotoil/__init__.py

      python -m build --wheel
      twine upload --repository-url $(FEED_URL) dist/*.whl
    displayName: 'Publish zerotoil-official (stable version)'
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    env:
      TWINE_USERNAME: 'build'
      TWINE_PASSWORD: $(System.AccessToken)
```

### Key Points

- **Every build** publishes `zerotoil` (dev) — available in Test/Stage
  immediately.
- **Only main branch builds** publish `zerotoil-official` in **two versions**:
  - `0.0.1.devYYMMDDHHMMSS` — dev version, for cross-referencing with the
    dev package from the same build.
  - `0.<BuildId>.0` — stable version (e.g., `0.1234.0`), for Prod to pin
    to a release that is easy to identify and roll back.

---

## How the Consumer (XAIOps) Resolves Packages

When a notebook job includes `ZEROTOIL_PACKAGE_VERSION`, the worker:

```
┌──────────────────────────────────────────────────────────┐
│ ZEROTOIL_PACKAGE_VERSION = "0.0.1.dev260428153042"       │
│   or                      "0.1234.0"  (stable)           │
│   or                      "latest"                       │
│ ZEROTOIL_USE_OFFICIAL = false (default)                   │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ Environment = "Prod"?                                     │
│   YES → pip install zerotoil-official==<version>          │
│   NO  → pip install zerotoil==<version>                   │
│                                                           │
│ Version = "latest" or ""?                                 │
│   YES → pip install zerotoil[-official]  (no pin, newest) │
│   NO  → pip install zerotoil[-official]==<exact>           │
│                                                           │
│ ZEROTOIL_USE_OFFICIAL = true? (non-prod only)             │
│   YES → pip install zerotoil-official==...                 │
│         (pre-prod test of official package)                │
└──────────────────────────────────────────────────────────┘
```

---

## Testing the Setup

### Publish locally (dev package)

```bash
# Stamp a test version
echo '__version__ = "0.0.1.dev990101000000"' > zerotoil/__init__.py

# Build
pip install build
python -m build --wheel

# Upload (need PIP_INDEX_URL or twine config)
twine upload --repository-url $FEED_URL dist/*.whl
```

### Verify in Test cluster

Submit a job with:
```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev990101000000"
}
```

### Verify official in Test cluster (pre-prod)

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260428153042",
  "ZEROTOIL_USE_OFFICIAL": true
}
```

### Verify in Prod

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "latest"
}
```

This will install the newest `zerotoil-official` from the feed.

---

## Security Model

```
Developer push to feature branch
  → Pipeline builds & publishes "zerotoil" (dev)
  → Test/Stage can use it immediately
  → Prod CANNOT use it (hard block in code)

PR merged to main
  → Pipeline builds & publishes BOTH packages
  → "zerotoil-official" becomes available to Prod
  → Test/Stage can validate with ZEROTOIL_USE_OFFICIAL=true

Key enforcement:
  - Package name separation (zerotoil vs zerotoil-official)
  - Only main branch pipeline publishes zerotoil-official
  - Worker code enforces: Prod → zerotoil-official, always
  - Version format validation: 0.0.1.devYYMMDDHHMMSS
```

---

## FAQ

**Q: Can someone manually `twine upload` a `zerotoil-official` package?**
A: Only if they have feed contributor rights. The `condition:` in the
pipeline limits *automated* publishing to main branch. For additional
protection, configure ADO feed permissions to restrict
`zerotoil-official` publishing to the pipeline's service account only.

**Q: What if I want to test a specific prod version in Test?**
A: Set `ZEROTOIL_USE_OFFICIAL=true` and the exact version:
```json
{"ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260428153042", "ZEROTOIL_USE_OFFICIAL": true}
```

**Q: What if I just set `"latest"` in Test?**
A: It installs the latest `zerotoil` (dev package), not official.

**Q: What if I set `"latest"` in Prod?**
A: It installs the latest `zerotoil-official`. This is safe because
only the official pipeline publishes to that package name.

**Q: Both packages provide `import zerotoil` — will they conflict?**
A: No. Only one is installed at a time. pip replaces the module files.
Since both packages use `packages = ["zerotoil"]`, the importable
module name is identical.
