# ZeroToil core framework (compact design)

The core framework provides a single base class (`TsgBase`) for representing a Troubleshooting Guide (TSG) as executable, composable code. Individual steps inside a TSG are plain methods — there is no per-step class. TSGs compose by calling other TSGs directly. Execution state lives on the TSG instance.

## Module

- Python module path: `zerotoil.core.framework`
- Implementation: a single file containing all base types

## Types

- `TsgInput` (Pydantic `BaseModel`)
  - Base has only `incident_id: str`.
  - Sub-TSGs subclass and add typed fields the parent prepares (e.g. `cluster_name: str`).
- `TsgOutput` (Pydantic `BaseModel`)
  - Base is empty.
  - Subclass and add typed result fields (e.g. `root_cause: str`).
No `TsgExecutionContext` — intermediate state is stored as instance fields on the TSG subclass itself.

## `TsgBase`

`TsgBase` is an ABC. Subclasses set `input_type` and `output_type` class attributes to declare their input/output types, which enables runtime validation.

| Attribute / Method | Signature | Purpose |
|---|---|---|
| **`input_type`** | `type[TsgInput]` (default `TsgInput`) | Declares the expected input type for this TSG. |
| **`output_type`** | `type[TsgOutput]` (default `TsgOutput`) | Declares the expected output type for this TSG. |
| **`__init__(dry_run=False)`** | keyword-only `dry_run: bool` | Enables read-only execution. When true, TSG code must skip mutating operations and print what would have happened. |
| **`run(tsg_input)`** | `TsgInput → TsgOutput` | Validates input type against `input_type` at runtime, then delegates to `_run()`. |
| **`_run(tsg_input)`** | `TsgInput → TsgOutput` | Abstract — implement TSG logic here. |
| **`run_for_incident(incident_id)`** | `str → TsgOutput` | Entry point for entry-level TSGs. Fetches the ICM incident, calls `_extract_input_from_incident()` to build a typed input, then delegates to `run()`. |
| **`_extract_input_from_incident(incident_id, incident)`** | `(str, Incident) → TsgInput` | Builds typed input from ICM incident. Default returns base `TsgInput`. Entry-level TSGs with richer inputs **must override** this to extract fields from `incident.Title`, `incident.Summary`, `incident.CreateDate`, or `incident.Descriptions`. |

### Runtime guards

- **`run()`** checks `isinstance(tsg_input, self.input_type)` before calling `_run()`. Passing the wrong input type raises `TypeError` immediately with a clear message.
- **`run_for_incident()`** fetches the ICM incident and delegates to `_extract_input_from_incident()`. If the override cannot extract a required field, it should raise `ValueError` with a clear message.

### Dry-run mode

`TsgBase(dry_run=True)` marks an execution as read-only. The framework prints `[DRY-RUN]` in the run banner and exposes `self.dry_run` to TSG implementations.

Dry-run mode is intentionally simple and explicit:

| Operation type | Dry-run behavior |
|---|---|
| Read-only data gathering (`DGrep`, `XDS`, Kusto, `get_account`, `icm.get_incident`) | Continue normally so the report contains real evidence. |
| ICM writes (`add_description`, `transfer`, `mitigate`) | Skip the call and print the exact action/evidence that would have been written. |
| Manual-action gates | Do not update incidents. Prefer printing the manual action that would have halted execution; individual TSGs may return instead of raising to allow dry-run exploration to continue. |

Generated TSG code must guard every mutating operation:

```python
if self.dry_run:
    print(f"  [DRY-RUN] Would post evidence to ICM {tsg_input.incident_id}")
    print(f"  [DRY-RUN] Evidence:\n{summary}")
else:
    incident = await icm.get_incident(int(tsg_input.incident_id), should_get_description=False)
    await incident.add_description(summary)
```

Dry-run is for safe validation against real incidents and tenants. It must not silently skip reads, because missing read evidence hides automation gaps.

### DGrep retry helper

`dgrep_query_with_retry(dgrep, **query_kwargs)` wraps `dgrep.query()` with exponential backoff for transient DGrep throttling. It retries only known throttle/transient signals such as HTTP 503, HTTP 429, `ServiceUnavailable`, `throttl`, or `Reached maximum number of outstanding queries from this client`. Non-throttle failures are raised immediately.

Use it for generated TSGs that issue DGrep queries, especially when the TSG searches multiple time chunks or multiple tenants:

```python
result = await dgrep_query_with_retry(
    dgrep,
    moniker=tenant,
    environment="Production",
    event_names="ServiceBackgroundActivityEvent",
    start_time=start_time,
    end_time=end_time,
    server_query=query,
)
```

### Incident input extraction

Entry-level TSGs whose `input_type` has fields beyond `incident_id` **must** override `_extract_input_from_incident()`. The TSG analysis document provides extraction examples in its `## Incident Input Extraction` section.

Two extraction strategies:

| Strategy | When to use | Implementation |
|---|---|---|
| **Regex** | Fields appear in a predictable format (e.g., tenant name after "in" in the title) | Use `re` from stdlib directly in the override |
| **LLM** | Fields are scattered across free-text descriptions or require semantic understanding | Use `xaiops.llm.execute_prompt` directly in the override |

No helper wrappers — extraction code lives directly in each TSG's `_extract_input_from_incident()` override using standard libraries. The code-writer agent reads the TSG extraction examples and decides which strategy to use.

## Composition rules

| Scenario | How it works |
|---|---|
| **Entry-level TSG** | `class MyTsg(TsgBase):` — Instantiate and call `tsg.run_for_incident(incident_id)`. Gathers everything else internally. |
| **Sub-TSG** | `class SubTsg(TsgBase):` with `input_type = SubInput` and `output_type = SubOutput` — Parent builds a typed input and calls `sub.run(sub_input)`. Reads results from the returned typed output. |
| **Internal steps** | Written as plain methods on the TSG class. Intermediate state stored on `self`. |

### Instance lifecycle

Each TSG instance should be used for **a single run**. Since intermediate state lives on `self`, reusing an instance carries stale state from a previous run. Always create a fresh instance per execution.

## Example

```python
import re
from typing import Any
from datetime import datetime
from zerotoil.core.framework import TsgBase, TsgInput, TsgOutput

# ── Sub-TSG with typed input/output ─────────────────────────

class CheckDeploymentInput(TsgInput):
    cluster_name: str

class CheckDeploymentOutput(TsgOutput):
    deployment_found: bool
    pipeline_url: str = ""

class CheckDeployment(TsgBase):
    input_type = CheckDeploymentInput
    output_type = CheckDeploymentOutput

    async def _run(self, tsg_input: CheckDeploymentInput) -> CheckDeploymentOutput:
        # use tsg_input.cluster_name ...
        return CheckDeploymentOutput(
            deployment_found=True,
            pipeline_url="https://...",
        )

# ── Entry-level TSG with incident input extraction ──────────

class InvestigateProcessCrashInput(TsgInput):
    cluster_name: str
    crash_time: datetime

class InvestigateProcessCrash(TsgBase):
    input_type = InvestigateProcessCrashInput
    output_type = TsgOutput

    # instance fields for intermediate state
    cluster: str = ""

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> InvestigateProcessCrashInput:
        """Extract cluster name from title, crash time from CreateDate."""
        title = incident.Title or ""
        match = re.search(r"cluster\s+(\S+)", title, re.IGNORECASE)
        if not match:
            raise ValueError(f"Cannot extract cluster_name from: {title!r}")
        return InvestigateProcessCrashInput(
            incident_id=incident_id,
            cluster_name=match.group(1),
            crash_time=incident.CreateDate,
        )

    async def _run(self, tsg_input: InvestigateProcessCrashInput) -> TsgOutput:
        self.cluster = tsg_input.cluster_name

        # call sub-TSG with typed input — one instance per call
        result = await CheckDeployment().run(CheckDeploymentInput(
            incident_id=tsg_input.incident_id,
            cluster_name=self.cluster,
        ))

        if result.deployment_found:
            ...  # mitigate

        return TsgOutput()

# ── Launch ──────────────────────────────────────────────────
# Only needs incident_id — extraction happens automatically
output = await InvestigateProcessCrash().run_for_incident("12345678")
```

## Design intent

- Keep primitives small and stable; generated TSG code depends on them.
- Strongly-typed inputs/outputs — no generic dicts; each TSG declares exactly what it needs and produces.
- Explicit `input_type` / `output_type` class attributes — simple, readable, no generic machinery.
- Runtime guards in `run()` and `run_for_incident()` catch type mismatches early with clear errors.
- No execution-context wrapper — the TSG instance *is* the context; intermediate state lives on `self`.
- Single-use instances — one instance per run, no stale state.
- Avoid class-per-step granularity — a TSG is the natural unit of composition and reuse.
- Allow layering safety/approval policies *outside* the core types (via higher-level orchestration).

## Mapping from TSG documents to code

Each TSG analysis folder under `zero-toil/tsgs/<tsg-id>/` maps to exactly one generated Python file under `zerotoil/tsgs/<tsg_id>.py`.

| TSG Document Element | Python Code Element |
|---|---|
| TSG `.md` file | One `TsgBase` subclass |
| `## Inputs` table | One `TsgInput` subclass (fields from the table) |
| `## Outputs` table | One `TsgOutput` subclass (fields from the table) |
| `## Incident Input Extraction` | `_extract_input_from_incident()` method on entry-level TSGs |
| `### Step N — <verb>` | One `_step_N_<name>(self)` method |
| `**Calls**: [tsg-name]` | Instantiate called TSG class and call `.run()` |
| `## Open Questions` | `# TODO:` comments in the generated code |
| `AUTOMATABLE: No` with reason | `print()` the manual action + `raise ManualActionRequired(...)` |

### Non-automatable steps

When a step's automation assessment says `AUTOMATABLE: No`, the generated method must:
1. Print a clear description of the required manual action to stdout.
2. Raise an exception to halt execution (the human must perform the action externally).

```python
def _step_1_acquire_jit_access(self) -> None:
    print("MANUAL ACTION REQUIRED: Acquire JIT access via https://aka.ms/JIT")
    print("  FFE / PlatformAdministrator for cluster: " + self.cluster_id)
    raise ManualActionRequired("JIT access must be acquired manually via portal")
```

### Coding ability usage

Each step's `CODING_ABILITY_DEPENDENCY` field maps to the corresponding `ABILITY.md` pattern. The code generator should:
1. Read the coding ability's sample code.
2. Replace placeholders with the step's input variables.
3. Wrap in the step method with proper error handling.
