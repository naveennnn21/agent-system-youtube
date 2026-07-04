# LangGraph Production Workflow

`create_shorts_workflow_graph()` builds the complete Shorts pipeline:

```text
Trend Agent
-> Script Agent
-> Voice Agent
-> Visual Agent
-> Video Editor
-> SEO Agent
-> Upload Agent
-> Analytics Agent
-> Learning Agent
```

## State

The workflow uses `WorkflowState` to carry:

- `metadata`
- `trend_results`
- `selected_topic`
- `script_draft`
- `voiceover`
- `visuals`
- `edited_video`
- `seo_metadata`
- `upload_result`
- `analytics_result`
- `learning_result`
- `errors`
- `monitoring`
- `messages`

## Error Handling And Retry

Each node runs through a shared retry wrapper. Defaults come from:

- `WORKFLOW_RETRY_ATTEMPTS`
- `WORKFLOW_RETRY_BASE_DELAY`
- `WORKFLOW_RETRY_MAX_DELAY`

When a node exhausts retries, the workflow records a structured error, appends
a failed monitoring event, sets `workflow_status=failed`, and routes directly to
`END`.

## Monitoring

Every node emits a monitoring event with:

- step
- status
- attempts
- duration in milliseconds
- error message when failed

These events are intentionally plain dictionaries so they can be logged,
persisted, or forwarded to an external monitoring system later.

## Dependency Injection

Agents can be injected through `metadata`, which keeps tests offline and lets
production callers swap specific providers:

```python
graph = create_shorts_workflow_graph()
result = await graph.ainvoke({
    "metadata": {
        "trend_agent": trend_agent,
        "script_agent": script_agent,
        "db_session": db_session,
    },
    "messages": [],
})
```

When an agent is not injected, the workflow creates the configured production
agent from settings.
