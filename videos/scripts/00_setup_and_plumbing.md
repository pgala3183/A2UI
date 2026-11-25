# Video script · Part 0 · Setup and shared plumbing (about 10 min)

## 0:00 Intro (1 min)

**Screen:** the root `README.md`, the 6 x 4 table.
**Say:** "Generative UI turns an agent's output into an interface. This repository has 24 codelabs: six technologies, each in four modes. Static: the model picks a component we built. Declarative: it composes from a catalog. Open-ended: it writes HTML. Mixed: catalog by default with one sandboxed generated region. And two separate decisions: what the model may generate (the columns) and how the UI reaches the user (the rows)."

## 1:00 Setup and the full test run (2 min)

**Run:**

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python run_all.py
```

**Say:** "Every codelab runs offline. 161 tests in 31 directories, each directory in its own process because the codelabs reuse file names on purpose." Point at "all green". Then:

```bash
python check_snippets.py
```

**Say:** "Every code snippet quoted in a README is checked against the real file, so the walkthroughs cannot drift from the code."

## 3:00 The model interface (2 min)

**Open:** `common/genui_common/llm.py`. Highlight the event list in the docstring, then `ScriptedLLM.stream`, then `get_llm`.
**Say:** "Every server consumes one event shape: text, tool_start, tool_delta, tool_end, done. ScriptedLLM replays the reply each codelab writes down, in small chunks with a delay, so streaming is visible and every run is the same. Set GENUI_LIVE=1 and the same servers call Claude instead."
**Show:** `ClaudeLLM.stream`: streaming, eager tool-input streaming, the refusal fallback.

## 5:00 The web server and the page shell (2 min)

**Open:** `common/genui_common/web.py`, the generator branch in `_send`. **Say:** "A route that returns a generator becomes a Server-Sent Events stream. Every /run in the course is a generator."
**Open:** `common/web/shell.mjs`. **Say:** "Every page has the same frame: prompt bar, the rendered surface, and on the right the wire panel: every message that crossed the network. Watch it in every video."

## 7:00 Sandboxing generated HTML (2 min)

**Open:** `common/genui_common/sandbox.py` (`check_html`, `inject_csp`), then `common/web/sandbox.mjs` (`mountSandbox`).
**Say:** "Three layers for model-written HTML: a content policy on the server, a CSP injected first in the head, and an iframe with sandbox allow-scripts and no allow-same-origin. A sandbox reduces capabilities; it does not make model output trustworthy. The document gets exactly two calls: genui.send and genui.onData."
**Open:** `common/web/morph.mjs`. **Say:** "Renderers rebuild the whole tree. morph keeps unchanged elements, focused inputs and live iframes in place."

## 9:00 Takeaway (30 s)

"The shared code is small and protocol-free. Everything you see in the next six videos is the protocol itself."
