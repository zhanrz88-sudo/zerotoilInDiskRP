# ADO Work Item Access

## Summary
Read, update, and comment on Azure DevOps work items using `az boards` CLI commands.

## Prerequisites
- Azure CLI with `azure-devops` extension installed
- Authenticated: `az login` (or `az devops login`)
- Default org/project can be set, but prefer explicit `--org` flag for clarity

## Read a Work Item

```bash
# Full JSON (all fields)
az boards work-item show --id <WORK_ITEM_ID> --org https://dev.azure.com/msazure

# Parse key fields with Python
az boards work-item show --id <WORK_ITEM_ID> --org https://dev.azure.com/msazure 2>&1 | python -c "
import sys,json
d=json.load(sys.stdin)
f=d.get('fields',{})
print('Type:', f.get('System.WorkItemType'))
print('Title:', f.get('System.Title'))
print('State:', f.get('System.State'))
print('Assigned:', f.get('System.AssignedTo',{}).get('displayName',''))
desc = f.get('System.Description','') or ''
print('Description:', desc[:3000])
"
```

### Important Flags
- `--fields` and `--expand` **cannot be used together** (causes error)
- Omit both to get all fields by default
- Description is HTML-encoded — strip tags if needed for plain text

## Update a Work Item

```bash
# Change state
az boards work-item update --id <WORK_ITEM_ID> --state Done --org https://dev.azure.com/msazure

# Change assigned-to
az boards work-item update --id <WORK_ITEM_ID> --assigned-to "alias@microsoft.com" --org https://dev.azure.com/msazure

# Multiple fields at once
az boards work-item update --id <WORK_ITEM_ID> --state Done --discussion "Completed via zerotoil automation" --org https://dev.azure.com/msazure
```

### Common State Values
| Work Item Type | States |
|---|---|
| Product Backlog Item | New → Approved → Committed → Done |
| Bug | New → Approved → Committed → Done |
| Task | New → Active → Closed |

## Add a Comment

```bash
az boards work-item update --id <WORK_ITEM_ID> --discussion "Your comment here" --org https://dev.azure.com/msazure
```

## Organization & Project Defaults
```bash
# Set defaults (optional — saves typing)
az devops configure --defaults organization=https://dev.azure.com/msazure project=One

# But prefer explicit --org for reliability in scripts
```

## Gotchas
- `web_fetch` **cannot** access ADO pages (requires auth). Always use `az boards` CLI.
- The `--fields` flag conflicts with `--expand` — use neither to get all fields.
- Description field contains raw HTML — use `[:3000]` slice to avoid flooding output.
- State values are case-sensitive and depend on the process template (Agile/Scrum/CMMI).
