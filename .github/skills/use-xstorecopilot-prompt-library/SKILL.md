---
name: use-xstorecopilot-prompt-library
description: "Use, create, and manage prompts in the XStore Copilot prompt library (xstore-copilot/prompts/). Covers the execute_prompt API from xaiops.llm, prompt JSON schema, Jinja2 templating, structured output, and best practices. USE FOR: execute_prompt, prompt library, create prompt, update prompt, add prompt, xaiops.llm, LLM prompt, structured output, prompt JSON, call GPT, call LLM from notebook."
---

# Use XStore Copilot Prompt Library

This skill teaches how to **find, understand, create, update, and call** prompts in the XStore Copilot prompt library.

## When to apply this skill

- Calling an LLM from a Jupyter notebook or Python code in this repo.
- Creating a new prompt definition for a notebook workflow.
- Updating an existing prompt (changing the template, model, or output schema).
- Understanding what a prompt does and how it is used.
- Debugging prompt execution failures.

## Key concepts

| Concept | Description |
|---|---|
| **Prompt library** | The `xstore-copilot/prompts/` folder in this repo. Contains `.json` files that define reusable LLM prompts. |
| **`execute_prompt`** | Async function from `xaiops.llm` that fetches a prompt JSON, renders it with Jinja2, calls the LLM, and returns the result. |
| **Prompt path** | A slash-prefixed path relative to `xstore-copilot/prompts/`. Example: `"/Xstore/Triage/collect-incident-info.json"` maps to `xstore-copilot/prompts/Xstore/Triage/collect-incident-info.json`. |
| **SharedPrompt schema** | The JSON structure every prompt file must follow: `template`, `model_configuration`, `output_configuration`. |

---

## Part 1 — Finding and understanding a prompt

### Where prompts live

```
xstore-copilot/prompts/
├── Sample/                          # Example/tutorial prompts
│   ├── checkingapproval.json
│   ├── identify-variables-from-python-code.json
│   └── poet.json
└── Xstore/                          # Production prompts organized by team
    ├── FE/                          # Front-End team prompts
    ├── Triage/                      # Auto-triage prompts
    ├── XAIOps/                      # AI Ops / Copilot prompts
    │   ├── Copilot/                 # XStore Copilot agent prompts
    │   ├── IncidentHub/             # Incident hub prompts
    │   └── XRHC/Copilot/           # XRHC log summarization
    ├── XCM/Decom/                   # Decommission reports
    ├── XFun/                        # XFun validation/bug classification
    ├── XScenarios/                  # SCTE, migrations, PR agent, reports
    └── XSMB/                        # SMB incident analysis
```

### How to read a prompt file

Every prompt JSON has three top-level keys:

```json
{
  "template": "...",              // The system prompt (Jinja2 template string)
  "model_configuration": { ... }, // Which model/version to use
  "output_configuration": { ... } // How to parse the LLM output
}
```

#### `template` — The system prompt

A plain string that becomes the LLM's system message. May contain **Jinja2 template variables** (`{{variable_name}}`) that get rendered at call time via the `parameters` argument.

Example from `Sample/poet.json`:
```
"template": "You are a poet. Given a topic, you can write an elegant poem.\n\nThe topic is: {{topic}}"
```

Example with data injection from `Xstore/XScenarios/SummarizeScteRegionalAccountCreationFailures.json`:
```
"template": "...Your task:\n1. Read and analyze all failures...\n\nINPUT DATA (JSON):\n{{ failures_json }}\n..."
```

#### `model_configuration` — Model settings

```json
{
  "model_deployment": "gpt-4.1",           // Model deployment name (required)
  "api_version": "2024-12-01-preview",     // Azure OpenAI API version (required)
  "api_parameters": {                      // Optional LLM parameters
    "temperature": 0,
    "top_p": 0.95
  }
}
```

Common model deployments: `"gpt-4.1"`, `"gpt-4o"`.

#### `output_configuration` — Output format

**Text output** (LLM returns a free-form string):
```json
{
  "output_format": "text",
  "output_examples": []
}
```

**JSON output** (LLM returns structured JSON matching a schema):
```json
{
  "output_format": "json",
  "output_json_schema": {
    "type": "object",
    "properties": {
      "field_name": { "type": "string", "description": "..." }
    },
    "required": ["field_name"],
    "additionalProperties": false
  },
  "output_examples": [
    "{\"field_name\": \"example_value\"}"
  ]
}
```

Key rules:
- `output_json_schema` uses standard JSON Schema. Always set `"additionalProperties": false` at the top level.
- `output_examples` is an array of example output strings. Helps the LLM understand the expected format. Can be empty `[]`.
- When `output_format` is `"json"` with a schema, `execute_prompt` sets `response_format` to structured JSON output mode.

### Finding which notebook uses a prompt

Search for the prompt path string in notebooks:
```
grep_search: "/Xstore/Triage/collect-incident-info.json" in jupyter-templates/
```

---

## Part 2 — Calling a prompt with `execute_prompt`

### Import

```python
from xaiops.llm import execute_prompt
```

### Function signature

```python
async def execute_prompt(
    prompt_path: str,                              # Path to prompt JSON (e.g. "/Xstore/Triage/collect-incident-info.json")
    user_input: str,                               # User message content
    parameters: Optional[dict[str, Any]] = None,   # Jinja2 template variables for system prompt
    overrides: Optional[dict[str, Any]] = None,    # Deep-merge overrides for prompt config
)
```

### Parameter details

| Parameter | Required | Description |
|---|---|---|
| `prompt_path` | Yes | Slash-prefixed path relative to `xstore-copilot/prompts/`. Leading `/` is conventional. |
| `user_input` | Yes | The user message string. This is the dynamic content specific to this call. |
| `parameters` | No | Dict of Jinja2 variables to render into the `template`. Keys must match `{{variable}}` names in the template. |
| `overrides` | No | Dict deep-merged into the prompt JSON, letting you override `model_configuration`, `output_configuration`, or even `template` at runtime. |

### Prompt resolution (how `prompt_path` maps to a file)

- **In AKS**: Fetched from blob storage cache of this repo's `main` branch.
- **Outside AKS** (local/XPortal): Fetched from Azure DevOps Git API for `main` branch.
- Both resolve to: `xstore-copilot/prompts/{prompt_path}`.

### Return value

The function returns a dict. The LLM output is under the `'response'` key:

- **Text format**: `response['response']` is a `str`.
- **JSON format**: `response['response']` is a parsed `dict` matching the schema.

### Usage patterns

**Basic call (user_input only)**:
```python
from xaiops.llm import execute_prompt

response = await execute_prompt(
    "/Xstore/XScenarios/summarizesctelogs.json",
    user_input=on_node_logs
)
summary = response['response']  # str (text output)
```

**With Jinja2 template parameters**:
```python
response = await execute_prompt(
    "/Xstore/Triage/AutoTriage-Report-Extractor.json",
    user_input=cleaned_content,
    parameters={
        "MonitorId": monitor_id
    }
)
extracted = response['response']  # dict (JSON output)
```

**With model overrides** (change model or temperature at runtime):
```python
response = await execute_prompt(
    "/Xstore/Triage/triage-incident-issue-type.json",
    user_input=incident_info,
    overrides={
        "model_configuration": {
            "model_deployment": "gpt-4o",
            "api_parameters": {"temperature": 0, "top_p": 0.95}
        }
    }
)
```

**Data-heavy call (parameters inject bulk data into template)**:
```python
response = await execute_prompt(
    "/Xstore/XScenarios/SummarizeScteRegionalAccountCreationFailures.json",
    user_input="",
    parameters={
        "failures_json": json.dumps(grouped_failures, default=str)
    }
)
root_causes = (response or {}).get("response", {}).get("root_causes") or []
```

**With retry wrapper** (for production reliability):
```python
async def execute_prompt_with_retry(*args, **kwargs):
    try:
        result = await execute_prompt(*args, **kwargs)
        if not result or ("response" in result and not result["response"]):
            raise ValueError("execute_prompt result is empty, triggering retry")
        return result
    except Exception as e:
        raise e
```

### Accessing response fields

```python
# Text output — response is a string
tsg_text = response['response']

# JSON output — response is a dict, access fields directly
team = response['response'].get('TriageTeam', None)
category = response['response']['Category']

# Merging two JSON prompt responses
combined = collect_response['response'] | issue_response['response']

# Parsing into a typed object
result = AgentEvaluationResult.parse_dict(response['response'])
```

---

## Part 3 — Creating a new prompt

### Step 1: Choose placement

Place the prompt JSON in the team folder that owns it:

```
xstore-copilot/prompts/Xstore/<TeamName>/<prompt-name>.json
```

- Use kebab-case for the filename (e.g., `categorize-failures.json`).
- If the team folder doesn't exist, create it and add an `owners.txt`.
- For experimentation, use `Sample/`.

### Step 2: Write the prompt JSON

Start from this template:

```json
{
  "template": "<system prompt text goes here>",
  "model_configuration": {
    "model_deployment": "gpt-4.1",
    "api_version": "2024-12-01-preview"
  },
  "output_configuration": {
    "output_format": "json",
    "output_json_schema": {
      "type": "object",
      "properties": {
        "field_name": {
          "type": "string",
          "description": "Description of this field."
        }
      },
      "required": ["field_name"],
      "additionalProperties": false
    },
    "output_examples": []
  }
}
```

Or for text output:

```json
{
  "template": "<system prompt text goes here>",
  "model_configuration": {
    "model_deployment": "gpt-4.1",
    "api_version": "2024-12-01-preview"
  },
  "output_configuration": {
    "output_format": "text",
    "output_examples": []
  }
}
```

### Step 3: Write the template

The `template` string is the system prompt. Best practices:

1. **Start with a role**: `"You are an AI assistant for the XStore/<Team> team."`
2. **Provide instructions**: numbered steps for what to do.
3. **Include background knowledge**: domain context the LLM needs.
4. **Define output format**: describe exact fields and constraints.
5. **Add anti-hallucination rules**: `"If you cannot determine a value, leave it empty. Do not guess."`
6. **Use Jinja2 variables** for dynamic content injected via `parameters`: `{{variable_name}}`.

#### When to use `user_input` vs `parameters`

| Use case | Mechanism | Example |
|---|---|---|
| **Dynamic content per call** (the "question") | `user_input` | Incident text, log content, code to analyze |
| **Static config that varies by context** | `parameters` (Jinja2 in template) | MonitorId, tenant name, mode flags |
| **Bulk data injected into the prompt** | `parameters` with `json.dumps()` | Large JSON arrays, failure lists |

### Step 4: Define the output schema (for JSON output)

Use JSON Schema in `output_json_schema`:

- Always include `"additionalProperties": false` at the object level.
- Use `"required"` to list all fields.
- Use `"enum"` for constrained string values.
- Use `"description"` on each property for clarity.
- Nested objects are supported — use `"type": "object"` with their own `"properties"`.
- Arrays use `"type": "array"` with `"items"`.

Example with nested structure and enums:

```json
{
  "type": "object",
  "properties": {
    "approved": {
      "type": "string",
      "enum": ["Yes", "No"],
      "description": "Whether the request was approved."
    },
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "score": { "type": "number" }
        },
        "required": ["name", "score"],
        "additionalProperties": false
      }
    }
  },
  "required": ["approved", "items"],
  "additionalProperties": false
}
```

### Step 5: Add output examples (optional but recommended)

Add 1-2 examples in `output_examples` as JSON strings. These get appended to the system prompt and help the LLM understand the expected format:

```json
"output_examples": [
  "{\"approved\": \"Yes\", \"items\": [{\"name\": \"foo\", \"score\": 0.9}]}"
]
```

### Step 6: Call from a notebook

```python
from xaiops.llm import execute_prompt

response = await execute_prompt(
    "/Xstore/<TeamName>/<prompt-name>.json",
    user_input=my_data
)
result = response['response']
```

---

## Part 4 — Updating an existing prompt

1. **Find the prompt JSON** in `xstore-copilot/prompts/`.
2. **Edit the fields** you need to change:
   - `template` — update instructions, add/remove Jinja2 variables.
   - `model_configuration` — change model deployment or API version.
   - `output_configuration` — adjust schema, add/remove fields, change format.
3. **Check all callers** — search for the prompt path in `jupyter-templates/` to find all notebooks that call it. Ensure your changes are backward-compatible.
4. **Test** — run the notebook that calls the prompt to verify the output.

### Common updates

| Change | What to edit |
|---|---|
| Improve prompt quality | Update `template` text with better instructions, examples, or constraints. |
| Add a new output field | Add to `output_json_schema.properties` and `required`. Update `template` to describe the new field. |
| Switch model | Change `model_configuration.model_deployment` (e.g., `"gpt-4o"` → `"gpt-4.1"`). |
| Add template variable | Add `{{new_var}}` in `template`, update callers to pass `parameters={"new_var": value}`. |
| Reduce hallucination | Add explicit anti-hallucination instructions in `template`. Set `"temperature": 0` in `api_parameters`. |

---

## Part 5 — Prompt design patterns from production

### Pattern: Incident information extraction

Used by AutoTriage. The template lists exact fields to extract with strict formatting rules.

```
Prompt: /Xstore/Triage/collect-incident-info.json
Input:  Incident title + summary + descriptions (as user_input)
Output: JSON with subscription, storage_account, team, etc.
Key:    Anti-hallucination rules, constrained team list, alias mapping.
```

### Pattern: Log summarization

Used by SCTE and XRHC. Sends raw logs as user_input, gets a concise summary.

```
Prompt: /Xstore/XScenarios/summarizesctelogs.json
Input:  Raw log text (as user_input)
Output: Text summary
Key:    Simple text output, no schema needed.
```

### Pattern: Multi-step pipeline

Used by AutoTriage report generation. Chains multiple prompts sequentially:

1. Extract structured data: `AutoTriage-Report-Extractor.json` → JSON
2. Render HTML report: `report-render-template.json` → text (HTML)

### Pattern: Classification with scoring

Used by PR agent. Classifies input into categories with numeric scores.

```
Prompt: /Xstore/XScenarios/categorize-pr-comments.json
Input:  PR comment text (as user_input)
Output: JSON with categories[] and scores[]
Key:    Detailed rubric in template, one-shot examples.
```

### Pattern: Query generation

Used by XStore Copilot. Generates DGrep queries from natural language.

```
Prompt: /Xstore/XAIOps/Copilot/generate-dgrep-query.json
Input:  User question (as user_input)
Output: JSON with query type, namespace, scope conditions, KQL/MQL query strings
Key:    Extensive MQL/KQL syntax reference in template, boolean flags.
```

---

## Hard rules

- **Never put secrets, keys, SAS tokens, or real customer data** in prompt templates. Use placeholders.
- **Do not invent team names** — constrain to known lists in the template.
- **Always set `additionalProperties: false`** in JSON schemas.
- **Keep prompts focused** — one prompt per task. Chain prompts for multi-step workflows.
- **Test after changes** — prompt changes affect all callers. Search for usage before modifying.
- **Use `gpt-4.1`** as the default model deployment unless there's a specific reason to use another.
- **Include `owners.txt`** in new team folders.

## Quality checklist

Before finishing, verify:

- [ ] Prompt JSON has all three required keys: `template`, `model_configuration`, `output_configuration`
- [ ] `model_deployment` and `api_version` are set in `model_configuration`
- [ ] `output_format` is either `"text"` or `"json"`
- [ ] If JSON output: `output_json_schema` has `additionalProperties: false` and all fields in `required`
- [ ] Jinja2 variables in `template` match the `parameters` dict passed by callers
- [ ] No secrets, PII, or real customer data in the template
- [ ] Template includes anti-hallucination instructions where appropriate
- [ ] Prompt file is placed in the correct team folder
- [ ] New team folders have an `owners.txt`
