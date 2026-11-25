# Video script · Part 2 · AG-UI (about 20 min)

## 0:00 What AG-UI is (2 min)

**Screen:** `codelabs/02_ag_ui/README.md`, the event list.
**Say:** "AG-UI is a transport. The page posts a RunAgentInput; the agent streams typed events: run lifecycle, text messages, tool calls, state snapshots and deltas, custom events. It has no components of its own: generative UI rides on these mechanisms."
**Open:** `_shared/agui.py` `model_events()`. "One model turn becomes AG-UI events; a text message always closes before a tool call."
**Mention:** the tests validate every event against the official `ag-ui-protocol` models.

## 2:00 Chapter 1 · Static: tool calls are components (4 min)

**Run:** `cd codelabs/02_ag_ui/01_static`, `python demo.py` (the event list). Then `$env:GENUI_DELAY = "0.08"`, `python server.py`, http://127.0.0.1:8201, Run. Watch the card fill in while TOOL_CALL_ARGS stream.
**Code:** `agent.py` backend vs render tools → `server.py` loop and `run_tool()` validation → `page/app.mjs` registry and `TOOL_CALL_ARGS` handler → `_shared/agui-client.mjs` `parsePartial`.
**Test:** `test_events_match_the_official_ag_ui_models`.
**Takeaway:** "A tool name maps to a pre-built component; the arguments are the props, drawn while they stream."

## 6:00 Chapter 2 · Declarative: the UI is shared state (5 min)

**Run:** `02_declarative`, `python demo.py`: point at the first run (one snapshot, eleven deltas) and the second (five replaces), and the byte counts. Then the page: Run, then "Only stations needing attention".
**Code:** `server.py` `ops_for()` (add vs diff) → catalog check and `ui.rejected` → re-validating the client's state → `agui-client.mjs` `STATE_DELTA` → `page/app.mjs` paint.
**Takeaway:** "Generative UI as state: snapshot once, then patch only what changed."

## 11:00 Chapter 3 · Open-ended: HTML over AG-UI (4 min)

**Run:** `03_open_ended`, http://127.0.0.1:8203, Run. Point at the source streaming in the dark box, then the CUSTOM genui.html event and the mounted calculator. Book a ride; point at the new run, the quote_ride tool, and the message inside the frame.
**Code:** `server.py` fence detection → CUSTOM events after TEXT_MESSAGE_END → `page/app.mjs` `split()`, mount, `genui.data` → `onAction` (a click is a user message) → `quote()`.
**Takeaway:** "The document travels twice: as text the user watches, and as a checked artifact the page runs."

## 15:00 Chapter 4 · Mixed: state, artifact, render tool, human in the loop (4 min)

**Run:** `04_mixed`, http://127.0.0.1:8204, Run. Point at the alert (render tool), the metrics (state), the simulator (artifact). Apply a plan in the simulator: the run ends with a confirm card. Confirm. Point at the metric change and the reply.
**Code:** `server.py` `lines_out` (one reply, three destinations) and `handle_line` → the frontend-tool break → `page/app.mjs` `FRONTEND_TOOLS`, `askOperator`, `addToolResult` → `after_rebalance()`.
**Takeaway:** "The page can be a tool. The agent asks, the operator answers, the next run continues."

## 19:00 Wrap-up (1 min)

`python run_all.py codelabs/02_ag_ui`. "AG-UI does not decide what the UI is. It decides how agent and page stay in sync."
