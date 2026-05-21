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

## Quick Start

### 1. Set up Python environment
```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -e ".[test,dev]" --extra-index-url <Storage-XI-feed-URL>
```

### 2. Run tests
```powershell
pytest
```

### 3. Submit a job to backend
```powershell
python scripts/run_zerotoil_job.py --tsg <tsg_module> --incident <id>
```

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
