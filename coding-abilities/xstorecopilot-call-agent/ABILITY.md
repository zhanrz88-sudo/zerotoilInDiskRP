---
name: XStoreCopilot - Call agent
description: Call an existing XStoreCopilot agent and return the thread id plus messages.
---

# Coding Ability: xstorecopilot-call-agent

## Description
Calls an existing XStoreCopilot agent (by name or GUID) with a user question and returns the conversation messages plus the created thread id.

- Intended for code generation building blocks.
- **Safety note**: this helper runs the agent in **auto-run** mode, which may execute tool-provided Python code in the current notebook/kernel.
- Use only with trusted agents/prompts, and prefer least-privilege credentials/data in the session.

Prereqs

- Run inside an environment where `xportal` is available (XPortal Jupyter / XScript runtime).
- You must be authenticated/authorized to call XStoreCopilot.

## Remarks

Interfaces (from `zero-toil/.venv/Lib/site-packages/xaiops/llm/xstorecopilot.py`)

- `await call_agent(agent_name: str, thread_id: str, full_question: str) -> dict`
	- `agent_name` can be either:
		- an agent GUID (validated by regex), or
		- a friendly agent name; the implementation resolves it to an id via `GET /api/v1/XCopilot/CallXCandyboxAPI/prod/agent/getAgent?agentId=<urlencoded>`.
	- `thread_id` is passed as `fork_from_thread_id` when creating a thread; in practice it may be `None` to start a new thread.
	- `full_question` is the user’s message to the agent.
	- The implementation uses the `prod` XStoreCopilot endpoint.

Related interface used internally

- `await XStoreCopilotClient.create_thread(agent_id, fork_from_thread_id: str = None) -> dict`

Return value shape (dictionary)

- `threadId: str` — the new thread id.
- `agentId: str` — the resolved agent id.
- `messages: list` — messages produced during auto-run (each item is typically a chat message dict).

## Sample Python code

```python
from xaiops.llm import call_agent

agent_name_or_id = "<agent_name_or_guid>"  # e.g. "XSSE Agent" or "00000000-0000-0000-0000-000000000000"
thread_id = None  # set to a prior result["threadId"] to continue/fork a conversation
question = "<your question for the agent>"

result = await call_agent(agent_name_or_id, thread_id, question)

# Common fields
result["threadId"]
result["agentId"]

# Last assistant message content (if present)
last_message = result["messages"][-1] if result.get("messages") else None
last_message.get("content") if isinstance(last_message, dict) else last_message
```
