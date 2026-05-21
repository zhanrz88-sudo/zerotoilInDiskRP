---
name: LLM Execute Prompt
description: Call an LLM via a managed prompt in the XStoreCopilot prompt library to extract structured information from unstructured text.
---

# Coding Ability: llm-execute-prompt

## Description

Executes a centrally managed prompt from the XStoreCopilot prompt library (`xstore-copilot/prompts/`) using `xaiops.llm.execute_prompt`. The prompt library stores reusable prompt definitions (system message, model config, output schema) as JSON files in the repo, so callers only provide the dynamic user input.

**When to use this instead of regex / pattern matching:**

- Input is unstructured natural language, HTML, markdown, or free-form log messages.
- The structure varies across instances (e.g., different incident monitors produce different report formats).
- You need to extract multiple fields at once and return them as a typed dict.
- Classification or decision-making is required (severity assessment, issue categorization, team routing).

**Safety notes:**

- Read-only — `execute_prompt` never mutates external state; it only calls the LLM.
- The prompt JSON is fetched from the repo's `main` branch (via blob cache in AKS, or Azure DevOps Git API locally).
- Never embed secrets or PII in `user_input` or `parameters`. Use placeholders when authoring prompt templates.
- LLM output can be non-deterministic. Always validate critical fields before acting on them.

**Prerequisites:**

- Run inside an environment where `xaiops` is available (XPortal Jupyter / XScript runtime).
- The target prompt JSON must already exist under `xstore-copilot/prompts/` on the `main` branch.

## Remarks

### Interface (from `zero-toil/.venv/Lib/site-packages/xaiops/llm/__init__.py`)

```python
async def execute_prompt(
    prompt_path: str,
    user_input: str,
    parameters: Optional[dict[str, Any]] = None,
    overrides: Optional[dict[str, Any]] = None,
) -> Union[dict, str]
```

| Parameter | Required | Type | Description |
|---|---|---|---|
| `prompt_path` | Yes | `str` | Path relative to `xstore-copilot/prompts/`. Leading `/` is stripped internally. Example: `"/Xstore/Triage/collect-incident-info.json"` or `"Xstore/Triage/collect-incident-info.json"` (both work). |
| `user_input` | Yes | `str` | The user message — the dynamic content for this specific invocation (e.g., the incident HTML body, a log snippet, an API response blob). |
| `parameters` | No | `dict` | Jinja2 template variables rendered into the `template` field. Keys must match `{{variable}}` placeholders in the prompt template. |
| `overrides` | No | `dict` | Deep-merged into the prompt JSON at runtime. Can override `model_configuration`, `output_configuration`, or `template`. |

### Return value

The return type depends on the prompt's `output_configuration.output_format`:

- **JSON output** (`output_format: "json"` + `output_json_schema` defined): returns a **`dict`** whose keys match the prompt's `output_json_schema` top-level properties. The raw LLM response text is parsed via `json.loads()`. OpenAI structured output (`strict: true`) constrains the schema.
- **Text output** (`output_format: "text"`): returns a **`str`** — the raw LLM text content.

**Important:** The return is the parsed content directly — there is **no** wrapper like `{"response": ...}`. For a JSON prompt with schema keys `{"subscription": ..., "storage_account": ...}`, you access `result["subscription"]` directly.

### Prompt JSON file schema (what goes in `xstore-copilot/prompts/<path>.json`)

Every prompt JSON file has three top-level keys:

```json
{
  "template": "You are ... {{optional_jinja_variable}} ...",
  "model_configuration": {
    "model_deployment": "gpt-4.1",
    "api_version": "2024-12-01-preview",
    "api_parameters": { "temperature": 0 }
  },
  "output_configuration": {
    "output_format": "json",
    "output_json_schema": { ... },
    "output_examples": [ "..." ]
  }
}
```

| Field | Description |
|---|---|
| `template` | System prompt. Supports Jinja2 syntax: `{{var}}` for parameters. Rendered before being sent to the LLM. |
| `model_configuration.model_deployment` | Azure OpenAI deployment name (e.g., `"gpt-4.1"`, `"gpt-4o"`, `"gpt-4o-mini"`). |
| `model_configuration.api_version` | Azure OpenAI API version string (e.g., `"2024-12-01-preview"`). |
| `model_configuration.api_parameters` | Optional dict of model parameters (e.g., `{"temperature": 0, "top_p": 0.95}`). Can be `null`. |
| `output_configuration.output_format` | `"json"` or `"text"`. |
| `output_configuration.output_json_schema` | JSON Schema object. Required when `output_format` is `"json"`. Sent to OpenAI as structured output with `strict: true`. **Must** set `"additionalProperties": false` on **all** object types in the schema. |
| `output_configuration.output_examples` | Optional list of example output strings. Appended to the system prompt as "Output Examples:" section. |

### How `overrides` works

The `overrides` dict is **deep-merged** into the fetched prompt JSON before execution. Common patterns:

- Switch model: `overrides={"model_configuration": {"model_deployment": "gpt-4o-mini"}}`
- Adjust temperature: `overrides={"model_configuration": {"api_parameters": {"temperature": 0}}}`
- Change output format at runtime: `overrides={"output_configuration": {"output_format": "text"}}`

### How `parameters` works (Jinja2 rendering)

If the prompt template contains `{{MonitorId}}`, pass `parameters={"MonitorId": "HighDiskQ99Latency"}`.
The template is rendered with Jinja2 before being sent as the system message.

### Execution flow (internal)

1. Fetch prompt JSON from `xstore-copilot/prompts/<prompt_path>` (blob cache in AKS, or ADO Git API locally).
2. Apply `overrides` via deep merge (if provided).
3. Render `template` with Jinja2 using `parameters` (if provided).
4. Append `output_examples` to the rendered system prompt (if defined).
5. Build chat-completion payload: `[{"role": "system", "content": rendered_prompt}, {"role": "user", "content": user_input}]`.
6. If JSON output + schema: add `response_format: {"type": "json_schema", "json_schema": {"name": "Response", "strict": true, "schema": output_json_schema}}`.
7. Call Azure OpenAI via `get_chat_completion(payload, model, api_version)`.
8. Return parsed JSON dict (for JSON format) or raw string (for text format).

## Sample Python code

### Pattern 1: Extract structured data from unstructured text (JSON output)

Use when the input is messy (HTML, logs, natural language) and you need a clean dict back.

```python
from xaiops.llm import execute_prompt

# The prompt at this path defines a JSON schema for the output
result = await execute_prompt(
    "/Xstore/Triage/AutoTriage-Report-Extractor.json",
    user_input=raw_report_content,
    parameters={
        "MonitorId": "<monitor_id>"
    }
)

# result is a dict with keys matching the prompt's output_json_schema
# e.g., result["Parameters"], result["Findings"], result["Actions"]
print(result)
```

Source: `jupyter-templates/Xstore/Triage/AutoTriageNewReport.ipynb`

### Pattern 2: Classify or categorize input (JSON output)

Use when you need the LLM to make a decision / pick from a set of options.

```python
from xaiops.llm import execute_prompt

result = await execute_prompt(
    "/Xstore/Triage/triage-incident-issue-type.json",
    user_input=incident_info,
    overrides={
        "model_configuration": {
            "model_deployment": "gpt-4o",
            "api_parameters": {"temperature": 0, "top_p": 0.95}
        }
    }
)

# result is a dict, e.g. {"Issue": "...", "IssueCategory": "...", "TriageTeam": "..."}
print(f"Team: {result['TriageTeam']}, Category: {result['IssueCategory']}")
```

Source: `jupyter-templates/Xstore/Triage/SummarizeIncidentInfo.ipynb`

### Pattern 3: Generate free-form text output (text output)

Use when you need the LLM to produce prose, HTML, markdown, etc.

```python
from xaiops.llm import execute_prompt
import json

result = await execute_prompt(
    "/Xstore/Triage/report-render-template.json",
    user_input=json.dumps(extracted_data, indent=2)
)

# result is a str (HTML content)
from IPython.display import HTML
HTML(result)
```

Source: `jupyter-templates/Xstore/Triage/AutoTriageNewReport.ipynb`

### Pattern 4: Override model or parameters at runtime

Use when you want to use a different model or tune parameters without changing the prompt file.

```python
from xaiops.llm import execute_prompt

result = await execute_prompt(
    "/Xstore/Triage/collect-incident-info.json",
    user_input=incident_info,
    overrides={
        "model_configuration": {
            "model_deployment": "gpt-4o",
            "api_parameters": {"temperature": 0, "top_p": 0.95}
        }
    }
)
```

Source: `jupyter-templates/Xstore/Triage/SummarizeIncidentInfo.ipynb`

### Pattern 5: Wrap with retry for robustness

Use in automation pipelines where transient LLM failures need retry.

```python
from xaiops.llm import execute_prompt
from XJupyter import common

@common.exponential_backoff()
async def execute_prompt_with_retry(*args, **kwargs):
    result = await execute_prompt(*args, **kwargs)
    if not result:
        raise ValueError("execute_prompt result is empty, triggering retry")
    return result

result = await execute_prompt_with_retry(
    "/Xstore/Triage/AutoTriage-Report-Extractor.json",
    user_input=raw_content,
    parameters={"MonitorId": "<monitor_id>"}
)
```

Source: `jupyter-templates/Xstore/Triage/AutoTriageNewReport.ipynb`

### Pattern 6: Chain two prompts (extract → render)

Use when you need to extract structured data, then feed it into a second prompt for rendering.

```python
from xaiops.llm import execute_prompt
import json

# Step 1: Extract structured JSON from raw content
extracted = await execute_prompt(
    "/Xstore/Triage/AutoTriage-Report-Extractor.json",
    user_input=cleaned_report_content,
    parameters={"MonitorId": "<monitor_id>"}
)

# Step 2: Generate HTML report from extracted data
html_report = await execute_prompt(
    "/Xstore/Triage/report-render-template.json",
    user_input=json.dumps(extracted, indent=2)
)

from IPython.display import HTML
HTML(html_report)
```

Source: `jupyter-templates/Xstore/Triage/AutoTriageNewReport.ipynb`
