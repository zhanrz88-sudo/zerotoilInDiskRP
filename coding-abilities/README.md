# ZeroToil coding abilities

This folder contains small, copy/paste-friendly **coding abilities** used as building blocks for code generation (e.g., when turning a TSG into runnable automation).

## Structure

- One subfolder per coding ability.
- Each coding ability folder contains an `ABILITY.md` that includes:
	- YAML front matter header (`name`, `description`)
	- **Description** (detailed; safety notes + prerequisites)
	- **Remarks** (interface signatures, types, key helpers)
	- **Sample Python code** (safe-by-default, placeholder inputs)

Optional subfolders (documentation/supporting content)

- `references/`: extra notes, query variants, sample result formats
- `assets/`: images, mock data, sample outputs

## Safety

- Samples are **read-only by default**.
- Never paste secrets, tokens, or customer data. Use placeholders like `<incident_id>`, `<cluster>`, `<tenant>`.

## Coding abilities

- `icm-get-incident/`: get an ICM incident, update severity/tags/description, mitigate, resolve, transfer
- `kusto-query/`: run a Kusto query (ADX)
- `dgrep-query/`: query DGrep logs
- `mdm-query/`: query MDM metrics (KQL-m)
- `ado-build-query/`: query Azure DevOps build pipelines, releases, and commits via `xportal.ado` and Kusto
- `xstorecopilot-call-agent/`: call an existing XStoreCopilot agent via `xaiops.llm.call_agent`
- `llm-execute-prompt/`: call an LLM via a managed prompt in the XStoreCopilot prompt library (`xaiops.llm.execute_prompt`) — extract structured data from unstructured text, classify/categorize input, generate text
- `xds-api-call/`: call XDS REST APIs (role instances, upgrade state, management role, XTable, etc.) via `xds_client`
- `xds-log-search/`: search XDS role-level logs (verbose, error, status, perf) via `xstore.xds` — `search_log`, `search_by_activity_id`, `generate_log_search_link`
- `storage-account-tenant-metadata/`: look up storage account metadata, resolve home storage tenant, find geo-pair tenant via `xstore.get_account` / `xstore.get_tenant`
- `geneva-action-call/`: execute Geneva Actions (ACIS) via `xportal.acis` — node recovery, config changes, GDCO tickets
