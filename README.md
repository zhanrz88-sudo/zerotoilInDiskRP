# ZeroToil for DiskRP

Automated TSG execution framework for DiskRP on-call engineers. Runs TSGs against live incidents via the XJupyterLite backend.

## Repository Structure

```
zerotoil/              # Python package source
  core/framework.py    # TsgBase class and execution engine
  tsgs/                # Executable TSG implementations
coding-abilities/      # API usage docs (ACIS, Kusto, DGrep, ICM, etc.)
scripts/               # Build, publish, and job submission scripts
tests/                 # Unit tests (pytest)
tsgs/                  # TSG analysis documents (markdown)
docs/                  # Framework and usage documentation
temp-workspace/        # Git-ignored scratch folder for temporary notebooks
.github/               # Copilot agents, skills, and instructions
```

## Setup

### First-time setup
```powershell
# From the repo root — creates .venv, installs all deps from Storage-XI-feed
.\scripts\prepare_env.ps1
```

This requires Python 3.12 and Azure CLI (`az login`). It installs `zerotoil` in editable mode plus internal packages (`xportal`, `xds-client`, `xstore`, `xaiops`, `xrhc`).

### Activate the environment
```powershell
.\.venv\Scripts\Activate.ps1
```

## Quick Test

### Unit test (no external dependencies, all APIs mocked)
```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests\tsgs\test_xkulfi_upgrade_action_failure.py
```

### Integration test with a real incident (~1-2 mins, requires network)
```powershell
.\.venv\Scripts\Activate.ps1
python -c "import asyncio; from zerotoil.tsgs.xkulfi_upgrade_action_failure import XKulfiUpgradeActionFailure; tsg = XKulfiUpgradeActionFailure(dry_run=True); asyncio.run(tsg.run_for_incident('783747141'))"
```

### Submit job to the XJupyterLite backend
```powershell
python scripts\run_zerotoil_job.py --notebook Xstore/zerotoil/tsgs/xkulfi_upgrade_action_failure.ipynb --environment test --params '{"incident_id":"783747141"}' -o
```

> **Tip:** Always use `dry_run=True` for first runs against live incidents. The backend worker has read-only claims — mutating operations (feature approvals, ICM transfers) require SAW with JIT.

## Key TSGs

| TSG | Module | Description |
|-----|--------|-------------|
| GetSubscriptionSettings | `get_subscription_settings` | Retrieve subscription settings via ACIS |
| ApproveFeatureRegistration | `approve_snapshot_immutability_feature` | Approve SnapshotImmutabilityPolicyPreview (SAW only) |
| Break ISF | `break_old_snapshot_families` | Break old snapshot families |
| CSM Quorum Loss | `csm_quorum_loss` | Handle CSM quorum loss incidents |

## Coding Abilities

Reference docs under `coding-abilities/` document API patterns for:
- DiskRP ACIS operations (Geneva Actions)
- Kusto queries (disks.kusto, disksbi.kusto)
- DGrep log search
- ICM incident management
- ADO work item access
- And more — see `coding-abilities/README.md`

## License

Internal Microsoft use only.
