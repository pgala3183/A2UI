# Part 0 · The shared plumbing

Every codelab imports a little shared code so that its own files contain only the idea it teaches. Nothing here is specific to a protocol. Read this once; the codelabs refer back to it.

## Python (`genui_common/`)

| File | What it gives you |
|---|---|
| `llm.py` | the model: `ScriptedLLM` (default, offline) and `ClaudeLLM` (`GENUI_LIVE=1`), one event shape for both |
| `web.py` | a standard-library HTTP server: routes, static mounts, JSON, and Server-Sent Events from generators |
| `sse.py` | SSE framing and parsing |
| `jsonpatch.py` | RFC 6901 pointers and RFC 6902 add/replace/remove/test, plus `diff()`; refuses `__proto__` keys |
| `sandbox.py` | `check_html()` (content policy for model-written HTML) and `inject_csp()` |
| `elements.py` | the element-map catalog used by AG-UI and the harness, with `check_spec()` and `prompt()` |
| `bikes.py` | the shared demo domain (a bike-share network) and the two HTML widgets a model writes |
| `tokens.py` | token counts with tiktoken `o200k_base` (falls back to chars/4 and says so) |
| `demo.py`, `testing.py` | helpers for demo scripts (headless browser, SSE client) and for running Node tests from pytest |

### The model interface

`genui_common/llm.py`:

```python
    {"type": "text", "text": "..."}                         a piece of reply text
    {"type": "tool_start", "id": "...", "name": "..."}      a tool call begins
    {"type": "tool_delta", "id": "...", "json": "..."}      a piece of its JSON input
    {"type": "tool_end", "id": "...", "name": "...", "input": {...}}
    {"type": "done", "stop_reason": "...", "content": [...], "usage": {...}}
```

Every server consumes this shape, so a server never knows which model runs. `ScriptedLLM` replays the reply each codelab writes down in its `respond()` function, in small chunks with a short delay, so streaming is visible and every run prints the same output. That is what the tests and recorded demos use: no network, no cost, reproducible.

`ClaudeLLM` sends the same system prompt and messages to the Claude API (default model `claude-opus-5-5`, low effort for UI generation, streaming with eager tool-input streaming, and the server-side refusal fallback enabled). Turn it on with:

```bash
set GENUI_LIVE=1                 # PowerShell: $env:GENUI_LIVE = "1"
set ANTHROPIC_API_KEY=...        # or an `ant auth login` profile
python server.py
```

Live runs cost money and their output differs from the recorded demos.

`genui_common/llm.py`:

```python
def get_llm(respond: Callable[[str, list[dict]], list[dict] | str]):
    """ClaudeLLM when GENUI_LIVE=1, otherwise a ScriptedLLM that calls ``respond``."""
    if os.environ.get("GENUI_LIVE") == "1":
        return ClaudeLLM()
    return ScriptedLLM(respond)
```

### Streams from generators

A route that returns a generator is streamed as Server-Sent Events; every codelab's `/run` is written that way.

`genui_common/web.py`:

```python
                if isinstance(result, types.GeneratorType):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
```

### The content policy for generated HTML

`genui_common/sandbox.py`:

```python
def check_html(html: str) -> list[str]:
    """Return the policy violations in ``html`` (empty list means it passes)."""
```

A sandbox reduces capabilities; it does not make arbitrary model output trustworthy. So generated HTML meets three layers: this policy on the server, a CSP `<meta>` injected first in `<head>`, and `<iframe sandbox="allow-scripts">` without `allow-same-origin` in the page.

## Browser (`web/`)

| File | What it gives you |
|---|---|
| `shell.mjs` | the page frame: prompt bar, chat, surface, and the **wire** panel that lists every message |
| `components.mjs` | the DOM widgets every renderer ends in (Card, Metric, Table, BarChart, StationCard...) |
| `elements.mjs` | `ElementView`: renders a flat element map through a registry |
| `morph.mjs` | re-render without losing state: keeps focused inputs and live iframes; `FrameHost` owns sandboxed frames |
| `sandbox.mjs` | `mountSandbox()`: the iframe, the CSP, and the `window.genui` bridge (`send`, `onData`) |
| `sse.mjs`, `jsonpatch.mjs`, `partial-json.mjs` | POST-based SSE reader, the JSON Patch twin, a tolerant parser for half-streamed JSON |

### The bridge every generated document gets

`web/sandbox.mjs`:

```js
    send(name, payload) { parent.postMessage({ genui: 1, type: 'action', name, payload: payload ?? {} }, '*'); },
    onData(fn) { listeners.push(fn); if (bridge.data !== undefined) fn(bridge.data); },
```

The same two calls work in all six themes. What happens behind them differs: an A2UI action envelope, an AG-UI user message, an MCP `tools/call`, a json-render state patch, an OpenUI statement, or a harness turn.

### Why `morph()`

Renderers here rebuild the whole tree on every change; it keeps them short. Rebuilding would reload every iframe and steal focus from every input, so `morph()` updates the live DOM in place and keeps any element whose key and signature did not change.

`web/morph.mjs`:

```js
  if (a.dataset.sig !== b.dataset.sig) return b; // props changed: take the new element
  if (a.dataset.frame !== undefined || a.tagName === 'IFRAME') return a; // frames are opaque
```

## Tests

```bash
python -m pytest -q common/tests     # Python helpers + the browser modules under node --test
```

Browser modules are tested in Node through `web/register.mjs`, which maps the URL paths the pages use (`/common/...`, `/shared/...`) onto files.
