---
name: zero-toil-create-update-pull-request
description: "Create or update a pull request for zero-toil changes. Covers git commit, PR creation via az cli or ADO MCP, monitoring PR build status, reading build logs to diagnose failures, and pushing fixes iteratively until the PR build passes. USE FOR: create PR, submit PR, push changes, commit and push, check PR build, fix PR build, update PR, git push, pull request, PR build failure, PR status."
---

# Zero-Toil Create/Update Pull Request

This skill handles the full PR lifecycle: commit changes, create a PR, monitor its build status, diagnose build failures from logs, fix issues, and iterate until the build passes.

## When to apply this skill

- After making code changes that need to be submitted as a pull request.
- When the user asks to commit, push, or create a PR.
- When diagnosing a PR build failure and pushing fixes.
- When monitoring PR build status and iterating on fixes.

## Prerequisites

- Git is configured with credentials for `https://msazure.visualstudio.com/One/_git/XScript-Templates`.
- Azure CLI (`az`) is installed with the `azure-devops` extension.
- ADO MCP server (`ado-mcp-msazure-org`) is configured for build status queries.
- The user is on a feature branch (not `main`).

## Workflow

### Step 1 — Commit changes

```bash
cd d:\gitroot\XScript-Templates
git add -A
git status                          # Review staged changes
git commit -m "<concise message>"   # Use conventional commit style
git push origin HEAD                # Push to remote
```

**Commit message conventions:**
- Keep the first line under 72 characters.
- Use imperative mood: "Fix test failures" not "Fixed test failures".
- Reference the context: "Fix ManualActionRequired propagation in failover TSG tests".

### Step 2 — Create a pull request

**Option A — Azure CLI (preferred, simpler):**

```bash
az repos pr create --repository XScript-Templates --source-branch <current-branch> --target-branch main --title "<PR title>" --description "<PR description>" --organization https://msazure.visualstudio.com --project One
```

Shorthand if already in the repo with defaults configured:

```bash
az repos pr create -t main --title "<PR title>"
```

**Option B — ADO MCP:**

Use the `mcp_ado-mcp-msazu_repo_create_pull_request` tool:
- `project`: `One`
- `repositoryId`: `XScript-Templates`
- `sourceRefName`: `refs/heads/<branch-name>`
- `targetRefName`: `refs/heads/main`
- `title`: PR title
- `description`: PR description

### Step 3 — Monitor PR build status

After PR creation, a build is triggered automatically. Monitor it:

**Option A — Azure CLI (recommended, more reliable):**

The PR build pipeline is `XScript-Templates-PullRequest`. Use `az pipelines` to find it and check builds.

1. **Get the pipeline definition ID** (one-time lookup):

   ```powershell
   az pipelines list `
     --organization "https://msazure.visualstudio.com/DefaultCollection" `
     --project One `
     --repository XScript-Templates --repository-type tfsgit `
     --query "[].{id:id, name:name}" -o table
   ```

   This returns two pipelines: `XScript-Templates-PullRequest` (PR validation) and `XScript-ADO-Sync`.

2. **List recent builds for the PR pipeline:**

   ```powershell
   $defId = az pipelines list `
     --organization "https://msazure.visualstudio.com/DefaultCollection" `
     --project One `
     --repository XScript-Templates --repository-type tfsgit `
     --name "XScript-Templates-PullRequest" `
     --query "[0].id" -o tsv 2>$null

   az pipelines build list `
     --organization "https://msazure.visualstudio.com/DefaultCollection" `
     --project One `
     --definition-ids $defId --top 5 `
     --query "[].{id:id, status:status, result:result, sourceBranch:sourceBranch, queueTime:queueTime}" `
     -o table
   ```

   Look for `sourceBranch` matching `refs/pull/<prId>/merge`.

3. **Check build result:**
   - `status: completed` + `result: succeeded` → PR is green ✅. Done.
   - `status: completed` + `result: failed` → proceed to Step 4.
   - `status: inProgress` → wait 30–60 seconds and re-run the query.

4. **If no build appears** for your PR after a force push or rebase, wait 30–60 seconds. The build queue may be delayed. If still missing after 2 minutes, the PR may not have a build policy configured.

> **Tip:** The `az` CLI requires the `azure-devops` extension. On ADO Server (on-prem), you may see a warning "does not support Azure DevOps Server" — this is cosmetic and the commands still work.

**Option B — ADO MCP:**

Use `mcp_ado-mcp-msazu_pipelines_get_builds` with:
- `project`: `One`
- `branchName`: `refs/pull/<prId>/merge`
- `top`: `5`

Then `mcp_ado-mcp-msazu_pipelines_get_build_status` with the `buildId` from above.

> **Note:** The ADO MCP tools can sometimes return errors or fail silently. If MCP calls fail, fall back to the `az` CLI approach above.

5. **If build succeeded** → PR is ready for review. Done.

6. **If build failed** → proceed to Step 4.

### Step 4 — Diagnose build failures

1. **Get build log list:**

   Use `mcp_ado-mcp-msazu_pipelines_get_build_log` with:
   - `project`: `One`
   - `buildId`: `<failed-buildId>`

   This returns a list of log entries with IDs and line counts.

2. **Find the failing step log:**

   Look for log entries with task names matching the failure (e.g., "Run zero-toil tests"). The build status usually mentions the failing job name.

3. **Read the specific log:**

   Use `mcp_ado-mcp-msazu_pipelines_get_build_log_by_id` with:
   - `project`: `One`
   - `buildId`: `<failed-buildId>`
   - `logId`: `<logId of the failing step>`

4. **Parse the failure:**
   - Look for `FAIL:`, `ERROR:`, `AssertionError`, `##[error]` lines.
   - Identify the root cause (test failure, syntax error, import error, pipeline config issue).

### Step 5 — Fix and re-push

1. Apply the fix locally.
2. Run tests locally to verify:

   ```bash
   cd d:\gitroot\XScript-Templates\zero-toil
   & .\.venv\Scripts\Activate.ps1
   pytest -v
   ```

3. Commit and push the fix:

   ```bash
   git add -A
   git commit -m "Fix: <description of fix>"
   git push origin HEAD
   ```

4. The PR build will re-trigger automatically. Go back to Step 3.

### Step 6 — Iterate until green

Repeat Steps 3-5 until the build passes. Common failure patterns:

| Failure | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: zerotoil` | PYTHONPATH not set in pipeline | Check `zero-toil-test.yml` working directory |
| `AssertionError` in tests | Code logic bug | Read the assertion message, fix the code |
| `Bash exited with code '141'` | SIGPIPE in pipeline script | Add `\|\| true` to piped commands under `set -euo pipefail` |
| `Bash exited with code '1'` | Test failures or script error | Read the full log for specific error |
| `ImportError` | Missing dependency | Check `pyproject.toml` dependencies |
| Pipeline YAML error | Syntax issue in `.pipeline/*.yml` | Validate YAML locally |
| ADO MCP tool errors | MCP server connectivity issue | Fall back to `az pipelines` CLI |

## ADO MCP tool reference

| Tool | Purpose |
|---|---|
| `mcp_ado-mcp-msazu_repo_create_pull_request` | Create a new PR |
| `mcp_ado-mcp-msazu_repo_get_pull_request_by_id` | Get PR details |
| `mcp_ado-mcp-msazu_repo_list_pull_requests_by_repo_or_project` | List PRs |
| `mcp_ado-mcp-msazu_pipelines_get_builds` | List builds for a branch |
| `mcp_ado-mcp-msazu_pipelines_get_build_status` | Get build result summary |
| `mcp_ado-mcp-msazu_pipelines_get_build_log` | List log entries for a build |
| `mcp_ado-mcp-msazu_pipelines_get_build_log_by_id` | Read a specific log entry |
| `mcp_ado-mcp-msazu_pipelines_get_build_definitions` | Find pipeline definition by name |

## Hard rules

- **Never push directly to `main`.** Always use a feature branch and PR.
- **Always run tests locally before pushing** to avoid unnecessary build cycles.
- **Do not force-push** (`git push --force`) unless explicitly asked — it rewrites history on shared branches.
- **Keep commits focused.** Each commit should address one logical change. Don't bundle unrelated fixes.
- **Do not include secrets, keys, or PII** in commit messages or PR descriptions.
