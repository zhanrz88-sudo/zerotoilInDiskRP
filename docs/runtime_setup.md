# ZeroToil runtime setup

This runtime supports **human-in-the-loop** automation for Xstore ICM incident mitigation TSGs. The environment is a Python virtual environment located at `zero-toil/.venv` and uses a unified dependency model:

- Public bootstrap packages for feed auth (`keyring`, `artifacts-keyring`)
- Runtime and test dependencies declared in `zero-toil/pyproject.toml`
- Internal packages (for example `xportal`, `xds-client`, `xstore`, `xaiops`, `xrhc`) are installed from `One/Storage-XI-feed`

## Prerequisites

- Local development: Windows + PowerShell
- Python 3.x (either `py` launcher or `python` in PATH)
- Azure CLI (`az`) installed (used for local `az login` authentication)
- Access to the `One/Storage-XI-feed` feed

## Local setup (PowerShell)

Run the setup script from the repo root (or any directory):

```powershell
.\zero-toil\scripts\prepare_env.ps1
```

What it does:

- Creates `zero-toil/.venv`
- Ensures local Azure CLI login (`az login` when needed)
- Installs `keyring` and `artifacts-keyring` from public PyPI (used for authenticating to Azure Artifacts feed)
- Installs zerotoil in editable mode with test dependencies (`pip install -e ".[test]"`) from `One/Storage-XI-feed`

## Activate

```powershell
Set-Location .\zero-toil
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
```

## Running tests

Tests are managed by **pytest** (configured in `pyproject.toml`). Three test markers control what runs:

| Marker | Scope | CI? |
|---|---|---|
| `unittest` | All APIs mocked, no external access | ✅ Default |
| `integrationtest` | Requires internal API access (XPortal, XDS, DGrep) | ❌ |
| `e2etest` | Full TSG execution against a live incident | ❌ |

```powershell
Set-Location .\zero-toil

# Run unit tests (default — same as CI)
pytest -v

# Run a specific test file
pytest tests/tsgs/test_failover_pending_transaction.py -v

# Run integration tests (requires API access)
pytest -m integrationtest -v

# Run everything (override default filter)
pytest -m "" -v
```

Tests without an explicit marker are automatically classified as `unittest` by `tests/conftest.py`.

## CI pipeline setup (YAML)

The YAML pipeline for ZeroToil is intended for **continuous integration testing**.

- Pipeline auth is handled by `PipAuthenticate@1`.
- In CI, no `az login` is required.
- In CI, no explicit `keyring` / `artifacts-keyring` bootstrap step is required.
- CI installs dependencies via `pip install -e ".[test]"` from the same `One/Storage-XI-feed` and runs `pytest -v` (which defaults to `-m unittest`).

Reference pipeline: `.pipeline/zero-toil-test.yml`

## Notes

- Keep runtime dependencies declared in `zero-toil/pyproject.toml` under `[project.dependencies]` so local and CI environments stay aligned.
- Test dependencies (pytest, pytest-asyncio) are in `[project.optional-dependencies] test`.
- `keyring` and `artifacts-keyring` are local bootstrap dependencies for feed auth and are intentionally installed by the setup script, not from `pyproject.toml`.
- If feed installation fails locally, verify you have permission to `One/Storage-XI-feed` and that your environment can authenticate to Azure Artifacts.
