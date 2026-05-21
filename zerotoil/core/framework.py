import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


async def dgrep_query_with_retry(
    dgrep,
    *,
    max_retries: int = 4,
    initial_backoff: float = 10.0,
    backoff_multiplier: float = 2.0,
    max_backoff: float = 120.0,
    **query_kwargs,
):
    """Call ``dgrep.query()`` with exponential backoff on throttle/transient errors.

    DGrep enforces a per-client outstanding query limit (typically 200).
    When the limit is hit the server returns HTTP 503 with
    ``"Reached maximum number of outstanding queries from this client"``.
    This helper retries with exponential backoff so callers don't need
    inline retry logic.

    Returns the DGrep query result on success, or raises the last
    exception after all retries are exhausted.
    """
    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            return await dgrep.query(**query_kwargs)
        except Exception as exc:
            err_msg = str(exc).lower()
            is_throttle = (
                "outstanding queries" in err_msg
                or "serviceunavailable" in err_msg
                or "503" in err_msg
                or "429" in err_msg
                or "throttl" in err_msg
            )
            if attempt == max_retries or not is_throttle:
                raise
            print(
                f"  [WARN] DGrep throttled (attempt {attempt}/{max_retries}): "
                f"retrying in {backoff:.0f}s ..."
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * backoff_multiplier, max_backoff)


class TsgInput(BaseModel):
    """Base input model.

    Entry-level TSGs need only ``incident_id``.
    Sub-TSGs subclass this and declare additional strongly-typed fields
    that the parent TSG populates before calling the sub-TSG.
    """

    model_config = ConfigDict(extra='forbid')

    incident_id: str


class TsgOutput(BaseModel):
    """Base output model.

    Subclass and declare strongly-typed fields for each TSG's results.
    """

    model_config = ConfigDict(extra='forbid')


def _format_model_fields(model: BaseModel, indent: int = 4) -> str:
    """Pretty-print a Pydantic model's fields for logging."""
    prefix = " " * indent
    data = model.model_dump() if hasattr(model, "model_dump") else model.dict()
    lines = []
    for name, value in data.items():
        display = repr(value)
        if len(display) > 200:
            display = display[:200] + "..."
        lines.append(f"{prefix}{name} = {display}")
    return "\n".join(lines)


class TsgBase(ABC):
    """Base class for all TSGs.

    Execution state lives on the instance — subclasses declare their own
    typed instance fields to hold intermediate data.  Each instance
    should be used for **a single run**; do not reuse instances.

    All methods are ``async`` because the runtime environment (XPortal
    Jupyter / XScript) is natively async.  Use ``await`` directly for
    xportal / xds_client API calls inside ``_run()`` and step methods.

    Set ``input_type`` and ``output_type`` to declare the expected
    input/output types::

        class MyTsg(TsgBase):
            input_type = MyInput
            output_type = MyOutput
            async def _run(self, tsg_input: MyInput) -> MyOutput: ...

    Entry-level TSGs override ``_extract_input_from_incident()`` to
    extract their typed input from an ICM incident.  This is the hook
    called by ``run_for_incident()``::

        class TopLevelTsg(TsgBase):
            input_type = MyInput
            output_type = MyOutput

            async def _extract_input_from_incident(
                self, incident_id: str, incident: Any,
            ) -> MyInput:
                # parse incident.Title / incident.Descriptions ...
                return MyInput(incident_id=str(incident.Id), ...)

            async def _run(self, tsg_input: MyInput) -> MyOutput: ...
    """

    input_type: type[TsgInput] = TsgInput
    output_type: type[TsgOutput] = TsgOutput

    def __init__(self, *, dry_run: bool = False):
        """Initialize the TSG instance.

        Args:
            dry_run: When True, skip all write/mutating operations
                (ICM updates, transfers, mitigations) and print what
                *would* have been done instead.  Read operations (DGrep,
                XDS, Kusto, get_account) proceed normally.
        """
        self.dry_run = dry_run

    async def run(self, tsg_input: TsgInput) -> TsgOutput:
        """Execute this TSG and return its output.

        Validates that *tsg_input* matches the declared ``input_type``,
        logs input/output, then delegates to ``_run()``.
        """
        tsg_name = type(self).__name__

        if not isinstance(tsg_input, self.input_type):
            raise TypeError(
                f"{tsg_name}.run() expects "
                f"{self.input_type.__name__}, got {type(tsg_input).__name__}"
            )

        print(f"\n{'=' * 60}")
        print(f"TSG START: {tsg_name}" + (" [DRY-RUN]" if self.dry_run else ""))
        print(f"{'=' * 60}")
        print(f"Input ({self.input_type.__name__}):")
        print(_format_model_fields(tsg_input))
        print()

        t0 = time.monotonic()
        result = await self._run(tsg_input)
        elapsed = time.monotonic() - t0

        print(f"\n{'=' * 60}")
        print(f"TSG END: {tsg_name}  ({elapsed:.1f}s)")
        print(f"{'=' * 60}")
        print(f"Output ({self.output_type.__name__}):")
        print(_format_model_fields(result))
        print()

        return result

    async def run_for_incident(self, incident_id: str) -> TsgOutput:
        """Entry point for entry-level TSGs.

        Fetches the ICM incident, calls
        ``_extract_input_from_incident()`` to build a typed input, then
        delegates to ``run()``.

        Entry-level TSGs that need parameters beyond ``incident_id``
        **must** override ``_extract_input_from_incident()`` to parse
        them from the incident title, summary, or description entries.

        Sub-TSGs (those whose ``input_type`` has required fields that
        cannot be extracted from an incident) should **not** be called
        via ``run_for_incident()`` — use ``run()`` with a typed input
        instead.
        """
        from xportal import icm as icm_client

        incident = await icm_client.get_incident(
            int(incident_id), should_get_description=True,
        )
        tsg_input = await self._extract_input_from_incident(
            incident_id, incident,
        )
        return await self.run(tsg_input)

    async def _extract_input_from_incident(
        self, incident_id: str, incident: Any,
    ) -> TsgInput:
        """Build a typed ``TsgInput`` from the ICM incident.

        **Default behaviour** — returns a plain ``TsgInput`` with only
        ``incident_id``.  This is sufficient when ``input_type`` is the
        base ``TsgInput``.

        **Override in entry-level TSGs** whose ``input_type`` has extra
        required fields.  The override should extract those fields from
        ``incident.Title``, ``incident.Summary``, ``incident.CreateDate``,
        and ``incident.Descriptions`` (a list of ``IncidentDescription``
        with ``.Text``, ``.ChangedBy``, ``.Date``).

        Extraction strategy (choose per-TSG):
        * **Regex** — when fields appear in a predictable format in the
          title or a description entry.  Use ``re`` from stdlib.
        * **LLM** — when fields are scattered across free-text
          descriptions or require semantic understanding.  Use
          ``xaiops.llm.execute_prompt`` from the prompt library.

        The TSG analysis document provides extraction examples in its
        ``## Incident Input Extraction`` section.  The code-writer
        agent reads those examples and generates the extraction code.
        """
        return TsgInput(incident_id=incident_id)

    async def run_step(self, step_method, *args, **kwargs):
        """Run a ``_step_N_*`` method with automatic logging.

        Handles both sync and async step methods.

        Usage inside ``_run()``::

            await self.run_step(self._step_1_do_something, tsg_input)

        Logs: step name, elapsed time, and any exception.
        """
        tsg_name = type(self).__name__
        step_name = step_method.__name__
        # Pretty name: _step_1_identify_offline_csms → Step 1: identify offline csms
        parts = step_name.lstrip("_").split("_", 2)
        if len(parts) >= 3 and parts[0] == "step":
            display = f"Step {parts[1]}: {parts[2].replace('_', ' ')}"
        else:
            display = step_name

        print(f"\n{'-' * 60}")
        print(f"[{tsg_name}] {display}")
        print(f"{'-' * 60}")

        t0 = time.monotonic()
        try:
            if inspect.iscoroutinefunction(step_method):
                result = await step_method(*args, **kwargs)
            else:
                result = step_method(*args, **kwargs)
            elapsed = time.monotonic() - t0
            print(f"[{tsg_name}] {display} OK ({elapsed:.1f}s)")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(f"[{tsg_name}] {display} FAILED ({elapsed:.1f}s) -- {type(exc).__name__}: {exc}")
            raise

    @abstractmethod
    async def _run(self, tsg_input: TsgInput) -> TsgOutput:
        """Implement TSG logic here.

        Store intermediate state on ``self``.  To delegate to a
        sub-TSG, instantiate it, build its typed input, and call
        ``await sub_tsg.run(sub_input)``.
        """
