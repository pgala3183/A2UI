"""AG-UI mixed mode: one agent loop, four kinds of generative UI.

    python server.py            then open http://127.0.0.1:8204

The agent splits the model's text line by line: JSON element lines become
STATE_DELTA patches, the artifact line becomes CUSTOM genui.html, and plain
sentences stream as chat. Tool calls are routed by kind: render tools get a
"rendered" result, backend tools run here, frontend tools end the run so the
page can ask the operator.
"""

from __future__ import annotations

import copy
import json

import agent
import agui
from genui_common import bikes, jsonpatch
from genui_common.sandbox import check_html
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="AG-UI mixed")
network = bikes.Network()
llm = agent.make_llm()
EMPTY = {"ui": {"root": None, "elements": {}}, "data": {}}


def stations() -> list[dict]:
    return [{"id": s["id"], "name": s["name"], "bikes": s["bikes"], "capacity": s["capacity"]} for s in network.stations]


def patch(state, ops):
    return jsonpatch.apply_patch(state, ops), agui.state_delta(ops)


def handle_line(state: dict, line: str):
    """One line of model output -> (new state, AG-UI events)."""
    item = json.loads(line)
    if "artifact" in item and "html" in item:
        problems = check_html(item["html"])
        if problems:
            return state, [agui.custom("genui.html.rejected", {"artifact": item["artifact"], "problems": problems})]
        return state, [agui.custom("genui.html", {"artifact": item["artifact"], "html": item["html"]})]
    element_id = item.pop("id")
    errors = agent.CATALOG.check_element(element_id, item)
    if errors:
        return state, [agui.custom("ui.rejected", {"id": element_id, "errors": errors})]
    path = f"/ui/elements/{element_id}"
    old = state["ui"]["elements"].get(element_id)
    ops = [{"op": "add", "path": path, "value": item}] if old is None else jsonpatch.diff(old, item, path)
    if state["ui"]["root"] is None:
        ops.insert(0, {"op": "replace", "path": "/ui/root", "value": element_id})
    state, event = patch(state, ops)
    return state, [event]


def after_rebalance(state: dict) -> tuple[dict, list]:
    """Application logic: new numbers into state after bikes moved."""
    summary = network.summary()
    new = copy.deepcopy(state)
    new["data"]["stations"] = stations()
    for element_id, value in (("m_bikes", f"{summary['bikes']} / {summary['capacity']}"),
                              ("m_attention", len(summary["needs_attention"]))):
        if element_id in new["ui"]["elements"]:
            new["ui"]["elements"][element_id]["props"]["value"] = value
    ops = jsonpatch.diff(state, new)
    return (new, [agui.state_delta(ops)]) if ops else (state, [])


@app.post("/agent")
def run_agent(request):
    run = agui.RunInput(request.json)
    yield agui.run_started(run.thread_id, run.run_id)
    state = run.state if isinstance(run.state.get("ui"), dict) else copy.deepcopy(EMPTY)
    if not state["ui"]["elements"]:
        state = copy.deepcopy(EMPTY)
        yield agui.state_snapshot(state)
    messages = run.anthropic_messages()
    frontend = {t["name"] for t in run.tools}
    tools = agent.TOOLS + run.frontend_tools()
    try:
        for _ in range(4):
            done, buffer, chat_id, chat_open = None, "", f"msg_{run.run_id}_{len(messages)}", False

            def lines_out(text_line):
                nonlocal state, chat_open
                if text_line.strip().startswith("{"):
                    state, events = handle_line(state, text_line)
                    return close_chat() + events
                if not text_line.strip():
                    return []
                events = [] if chat_open else [agui.text_start(chat_id)]
                chat_open = True
                return events + [agui.text_content(chat_id, text_line + "\n")]

            def close_chat():
                """AG-UI keeps event kinds apart: end the text message before state or tool events."""
                nonlocal chat_open, chat_id
                if not chat_open:
                    return []
                chat_open = False
                closed, chat_id = chat_id, chat_id + "_next"
                return [agui.text_end(closed)]

            for event, final in agui.model_events(llm, agent.system_for(state), messages, tools, chat_id):
                if event is None:
                    done = final
                elif event["type"] == "TEXT_MESSAGE_CONTENT":
                    buffer += event["delta"]
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        yield from lines_out(line)
                elif event["type"] not in ("TEXT_MESSAGE_START", "TEXT_MESSAGE_END"):
                    if event["type"] == "TOOL_CALL_START":
                        yield from lines_out(buffer)
                        buffer = ""
                        yield from close_chat()
                    yield event  # tool call events pass through untouched
            yield from lines_out(buffer)
            yield from close_chat()
            if state["ui"]["elements"] and not state["data"].get("stations"):
                state, event = patch(state, [{"op": "add", "path": "/data/stations", "value": stations()}])
                yield event
            messages.append({"role": "assistant", "content": done["content"]})
            calls = [b for b in done["content"] if b["type"] == "tool_use"]
            if not calls or any(c["name"] in frontend for c in calls):
                break  # nothing to run, or the page must answer a frontend tool first
            results = []
            for call in calls:
                if call["name"] == "rebalance":
                    result = network.rebalance(call["input"]["from"], call["input"]["to"], call["input"]["count"])
                    if result["ok"]:
                        state, events = after_rebalance(state)
                        yield from events
                else:
                    result = {"rendered": call["name"]}
                yield agui.tool_result(call["id"], result)
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": json.dumps(result)})
            messages.append({"role": "user", "content": results})
            if all(c["name"] in agent.RENDER_TOOLS for c in calls):
                break
        yield agui.run_finished(run.thread_id, run.run_id)
    except Exception as error:
        yield agui.run_error(str(error))


if __name__ == "__main__":
    app.run(port_from_argv(8204))
