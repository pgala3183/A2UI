"""AG-UI static mode: one endpoint, a stream of typed events.

    python server.py            then open http://127.0.0.1:8201

POST /agent takes an AG-UI RunAgentInput and runs a small agent loop:
model turn -> tool calls -> results -> next model turn. Backend tools run
here; render tools were drawn by the page, so their result just says so.
"""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

import agent
import agui
from genui_common import bikes
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="AG-UI static")
network = bikes.Network()
llm = agent.make_llm()
SCHEMAS = {t["name"]: Draft202012Validator(t["input_schema"]) for t in agent.TOOLS}


def run_tool(call: dict) -> tuple[str, bool]:
    """Returns (content, is_error). Inputs are validated before anything runs."""
    errors = [e.message for e in SCHEMAS[call["name"]].iter_errors(call["input"])]
    if errors:
        return json.dumps({"error": errors}), True
    if call["name"] == "get_station":
        v = network.view(call["input"]["station_id"])
        return json.dumps({**{k: v[k] for k in ("name", "bikes", "capacity", "status", "hourly")}, "hours": bikes.HOURS}), False
    return json.dumps({"rendered": call["name"]}), False  # a render tool: the page drew it


@app.post("/agent")
def run_agent(request):
    run = agui.RunInput(request.json)
    yield agui.run_started(run.thread_id, run.run_id)
    messages = run.anthropic_messages()
    try:
        for _ in range(4):  # a few model turns at most
            done = None
            for event, final in agui.model_events(llm, agent.SYSTEM, messages, agent.TOOLS):
                if event:
                    yield event
                else:
                    done = final
            messages.append({"role": "assistant", "content": done["content"]})
            calls = [b for b in done["content"] if b["type"] == "tool_use"]
            if not calls:
                break
            results = []
            for call in calls:
                content, is_error = run_tool(call)
                yield agui.tool_result(call["id"], content)
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": content, "is_error": is_error})
            messages.append({"role": "user", "content": results})
            if all(c["name"] in agent.RENDER_TOOLS for c in calls):
                break  # the UI is on screen; the model has nothing new to read
        yield agui.run_finished(run.thread_id, run.run_id)
    except Exception as error:  # a run always ends with RUN_FINISHED or RUN_ERROR
        yield agui.run_error(str(error))


if __name__ == "__main__":
    app.run(port_from_argv(8201))
