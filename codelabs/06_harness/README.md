# Theme 06 · Harness integration: generative UI inside the agent loop

The previous themes were UI formats and transports. This theme puts generative UI where a coding agent lives: inside a **harness**, the loop that calls the model, runs tools, asks for permission and keeps the conversation. UI becomes tools the model can call, and the harness draws their output on **two surfaces at once**: a terminal (rich, ASCII) and a web page (SSE).

```text
user -> harness.ask()
          model turn -> tool calls -> [permission?] -> tool results -> model turn -> ...
          every step is an event: text | tool_call | tool_result | ui | permission_request | done
          events -> TerminalSurface.handle()   and   SSE -> web page
UI action from a surface -> harness.ui_action(view, action) -> only if that view declared the action
```

## The four modes in the harness

| Codelab | Mode | The UI tools | New idea |
|---|---|---|---|
| [01_static](01_static/README.md) | static | `show_metric`, `show_table`, `show_chart` | render tools; one agent, two surfaces |
| [02_declarative](02_declarative/README.md) | declarative | `render_ui(view, spec)` | invalid specs are error results; the model fixes them inside the loop |
| [03_open_ended](03_open_ended/README.md) | open-ended | `render_html(...)` (permission: ask), `send_to_view` | a permission gate, declared actions, artifacts served with a `sandbox` CSP header |
| [04_mixed](04_mixed/README.md) | mixed | all of the above + `rebalance` (ask) | rendering is allowed; side effects wait for the user |

## Shared code (`_shared/harness/`)

| File | Role |
|---|---|
| `tools.py` | `Tool` (JSON Schema validation, `permission`, `(result, ui_events)` returns), `Registry`, `ToolError` |
| `loop.py` | `Harness`: `ask()`, `resume(id, approve)`, `ui_action(view, action, params)`; the loop is a generator of events |
| `terminal.py` | `TerminalSurface` (rich renderables with ASCII boxes), `run_cli()` with y/N permission prompts |
| `web.py` | the web surface: `/run`, `/approve`, `/ui-action`, `/artifacts/*`; the server's terminal mirrors every event |
| `../client.mjs` | the page: transcript, `ui` events, permission cards |

`_shared/harness/loop.py`:

```python
            elif tool.permission == "ask" and call["id"] not in self.approved:
                self.pending = {"calls": calls, "index": index, "results": results}
                yield {"type": "permission_request", "id": call["id"], "name": call["name"], "input": call["input"]}
                return True
```

A tool marked `ask` pauses the loop. `resume()` continues exactly where it stopped, with the same batch of calls.

## Run the theme

```bash
python run_all.py codelabs/06_harness
cd codelabs/06_harness/01_static && python cli.py "Which stations need rebalancing?"   # terminal surface
cd codelabs/06_harness/01_static && python server.py                                    # web + mirrored terminal
```

Ports: 8601 (static), 8602 (declarative), 8603 (open-ended), 8604 (mixed).
