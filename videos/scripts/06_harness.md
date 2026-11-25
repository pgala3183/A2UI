# Video script · Part 6 · Harness integration (about 20 min)

## 0:00 What the harness adds (2 min)

**Screen:** `codelabs/06_harness/README.md`, the loop diagram.
**Say:** "A harness is the loop a coding agent lives in: call the model, run tools, ask for permission, keep the conversation. Here generative UI becomes tools, and every event is drawn on two surfaces: the terminal and the browser."
**Open:** `_shared/harness/loop.py`: `_loop`, `_run_calls`, the permission pause.

## 2:00 Chapter 1 · Static: render tools (4 min)

**Run:** `cd codelabs/06_harness/01_static`, `python cli.py "Which stations need rebalancing?"` (rich output in the terminal).
**Run:** `python server.py`, http://127.0.0.1:8601, Run. Put the browser and the server's terminal side by side: the same events on two surfaces.
**Code:** `agent.py` `show_table` (result + ui event) → `tools.py` validation → `loop.py` forwarding ui events → `terminal.py` Table → `client.mjs` component → `web.py` `relay()`.
**Takeaway:** "One agent, two surfaces. The model reads a summary; the user sees the component."

## 6:00 Chapter 2 · Declarative: render_ui (4 min)

**Run:** `02_declarative`, `python cli.py "Make me a rebalancing report"`. Point at the error result (PieChart, footer), the model's fix, and the rendered panel.
**Code:** `agent.py` `render_ui` → `elements.py` check → `ToolError` → `terminal.py` spec rendering.
**Takeaway:** "Validation errors are tool results; the loop corrects itself."

## 10:00 Chapter 3 · Open-ended: render_html with permission (5 min)

**Run:** `03_open_ended`, `python cli.py "Make me an interactive trip-cost calculator"`; answer `n`, then run again and answer `y`. Then `python server.py`, http://127.0.0.1:8603: approve the card, use the calculator, book.
**Show:** open http://127.0.0.1:8603/artifacts/calc.html and the response's CSP header in DevTools (Network tab).
**Code:** `agent.py` `permission="ask"` and policy → `loop.py` `resume()` → declared actions in `ui_action()` → `web.py` `HEADER_CSP`.
**Takeaway:** "Generated code is a tool call like a shell command: it can wait for a yes."

## 15:00 Chapter 4 · Mixed: the whole loop (4 min)

**Run:** `04_mixed`, http://127.0.0.1:8604, Run: alert, desk, embedded simulator. Apply a plan: the permission card appears and nothing moves yet. Approve: the desk updates, the simulator keeps its selection. Click Refresh numbers.
**Code:** `rebalance` with `ask` → GeneratedView needs its artifact → one turn with all three modes → `client.mjs` embedded placement and data.
**Takeaway:** "Render freely, act with permission, and accept only actions a view declared."

## 19:00 Wrap-up of the course (1 min)

`python run_all.py` (all 31 directories green). Back to the root README table. "Six technologies, four modes, one domain. Choose the representation, choose the transport, and keep the application in charge of what runs."
