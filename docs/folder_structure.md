# ZeroToil folder structure

This folder layout keeps environment setup, design docs, test assets, and generated automation code clearly separated.

## Layout

```text
zero-toil/
  .venv/        # Local Python virtual environment
  artifacts/    # Downloaded wheel packages from Azure DevOps
  docs/         # Design and usage documentation
  scripts/      # Environment prep, build, and test scripts
  coding-abilities/ # Codegen building blocks (one folder per skill, each with ABILITY.md)
  pyproject.toml    # Project metadata, dependencies, and pytest configuration
  tests/        # Python test modules
    conftest.py       # Pytest config: auto-applies 'unittest' marker to unmarked tests
  tsgs/         # TSG analysis documents organized by tsg-id
    <tsg-id>/         # One folder per TSG (one source document = one folder)
      <tsg-id>.md     # Main TSG document (maps to one TsgBase subclass)
      README.md       # Call graph, design principles, source links
      _references.md  # Shared constants (Kusto endpoints, Geneva Actions, contacts)
      steps/          # Per-step automation analysis
        step-N-<verb-phrase>.md  # I/O, processing logic, automation assessment
  zerotoil/     # Root Python module: framework + generated TSG code
    core/
      framework.py    # TsgBase, TsgInput, TsgOutput base classes
    tsgs/             # Generated TSG Python code (one file per TSG)
      <tsg_id>.py     # Generated TsgBase subclass
```

## Conventions

- Keep `.venv/` and `artifacts/` local-only (do not treat as source).
- Put "how to run" guidance in `docs/` (see `runtime_setup.md`).
- Place shared framework code in `zerotoil/core/`, and generated TSG code under `zerotoil/tsgs/`.
- Each TSG analysis folder under `tsgs/` maps 1:1 to a generated Python file under `zerotoil/tsgs/`.
- TSG analysis documents use kebab-case (`csm-quorum-loss`); generated Python files use snake_case (`csm_quorum_loss.py`).
