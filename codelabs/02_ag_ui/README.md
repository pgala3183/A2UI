# Theme 02 · AG-UI: typed events between an agent and a page

[AG-UI](https://docs.ag-ui.com) (Agent-User Interaction protocol, from CopilotKit) is a **transport**. The page POSTs a `RunAgentInput` (thread, run, messages, state, frontend tools, context); the agent answers with a stream of typed events over Server-Sent Events:

```text
RUN_STARTED
  TEXT_MESSAGE_START / TEXT_MESSAGE_CONTENT (delta) / TEXT_MESSAGE_END
  TOOL_CALL_START / TOOL_CALL_ARGS (delta) / TOOL_CALL_END / TOOL_CALL_RESULT
  STATE_SNAPSHOT / STATE_DELTA (RFC 6902 JSON Patch)
  STEP_STARTED / STEP_FINISHED, CUSTOM {name, value}
RUN_FINISHED  (or RUN_ERROR)
```

AG-UI does not define components. Generative UI rides on its mechanisms: tool calls the page renders, shared state the page renders, and custom events. The events here are written by hand so every field is visible; each codelab's tests validate them against the official `ag-ui-protocol` Pydantic models (`ag_ui.core.Event`).

## The four modes in AG-UI

| Codelab | Mode | AG-UI mechanism | New idea |
|---|---|---|---|
| [01_static](01_static/README.md) | static | `TOOL_CALL_*` for render tools | tool name → pre-built component, drawn while the arguments stream |
| [02_declarative](02_declarative/README.md) | declarative | `STATE_SNAPSHOT` + `STATE_DELTA` | the UI is shared state; the next run patches only what changed |
| [03_open_ended](03_open_ended/README.md) | open-ended | `TEXT_MESSAGE_*` + `CUSTOM genui.html` | HTML streams as text; the checked document arrives as one custom event |
| [04_mixed](04_mixed/README.md) | mixed | all of the above + a frontend tool | human in the loop: the run ends on `confirm_rebalance`, the answer starts the next run |

## Shared code (`_shared/`)

| File | Role |
|---|---|
| `agui.py` | event builders with camelCase fields, `RunInput` (parses `RunAgentInput`, converts history to Messages API turns), `model_events()` (one model turn → AG-UI events) |
| `agui-client.mjs` | `HttpAgent`: the part of `@ag-ui/client` these codelabs use: POST, read SSE, keep `messages`, `state`, `toolCalls` |
| `page.mjs` | the page loop: wire log, chat bubbles, and per-codelab event handlers |

`_shared/agui.py`:

```python
    for e in llm.stream(system, messages, tools):
        if e["type"] == "text":
            if not open_text:
                open_text = True
                yield text_start(message_id), None
            yield text_content(message_id, e["text"]), None
        elif e["type"] == "tool_start":
            if open_text:
                open_text = False
                yield text_end(message_id), None
            yield tool_start(e["id"], e["name"], message_id), None
```

A text message is always closed before a tool call starts; AG-UI keeps one message's events together.

## Run the theme

```bash
python run_all.py codelabs/02_ag_ui
cd codelabs/02_ag_ui/01_static && python demo.py
cd codelabs/02_ag_ui/01_static && python server.py     # http://127.0.0.1:8201
```

Ports: 8201 (static), 8202 (declarative), 8203 (open-ended), 8204 (mixed).
