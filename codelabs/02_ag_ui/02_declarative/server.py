"""AG-UI declarative mode: model output -> validated elements -> STATE_DELTA.

    python server.py            then open http://127.0.0.1:8202

The page owns the state between runs (it sends it in RunAgentInput.state).
The server never trusts it blindly: it is re-validated, and every element
the model writes is checked against the catalog before it becomes a patch.
"""

from __future__ import annotations

import copy
import json

import agent
import agui
from genui_common import jsonpatch
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="AG-UI declarative")
llm = agent.make_llm()
EMPTY = {"ui": {"root": None, "elements": {}}}


def lines(events):
    buffer = ""
    for e in events:
        if e["type"] == "text":
            buffer += e["text"]
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    yield line.strip()
    if buffer.strip():
        yield buffer.strip()


def ops_for(state: dict, element_id: str, element: dict) -> list[dict]:
    """add for a new element, a minimal diff for one that changed."""
    path = f"/ui/elements/{jsonpatch._escape(element_id)}"
    old = state["ui"]["elements"].get(element_id)
    ops = [{"op": "add", "path": path, "value": element}] if old is None else jsonpatch.diff(old, element, path)
    if state["ui"]["root"] is None:
        ops.insert(0, {"op": "replace", "path": "/ui/root", "value": element_id})
    return ops


@app.post("/agent")
def run_agent(request):
    run = agui.RunInput(request.json)
    yield agui.run_started(run.thread_id, run.run_id)
    state = run.state if isinstance(run.state.get("ui"), dict) else copy.deepcopy(EMPTY)
    if agent.CATALOG.check_spec(state["ui"]) and state["ui"]["elements"]:
        state = copy.deepcopy(EMPTY)  # the client sent something broken: start over
    if not state["ui"]["elements"]:
        yield agui.state_snapshot(state)  # the starting point every delta applies to
    yield agui.step_started("write_ui")
    written, rejected, patches = 0, [], 0
    for line in lines(llm.stream(agent.system_for(state), run.anthropic_messages())):
        try:
            element = json.loads(line)
            element_id = element.pop("id")
        except (ValueError, KeyError, AttributeError):
            rejected.append({"line": line[:80], "error": "not an element object with an id"})
            continue
        errors = agent.CATALOG.check_element(element_id, element)
        if errors:
            rejected.append({"id": element_id, "errors": errors})
            yield agui.custom("ui.rejected", rejected[-1])
            continue
        ops = ops_for(state, element_id, element)
        if ops:
            state = jsonpatch.apply_patch(state, ops)
            patches += len(ops)
            yield agui.state_delta(ops)
        written += 1
    yield agui.step_finished("write_ui")
    problems = agent.CATALOG.check_spec(state["ui"])
    message_id = f"msg_{run.run_id}"
    yield agui.text_start(message_id)
    summary = f"Updated {written} elements with {patches} patch operations."
    yield agui.text_content(message_id, summary + (f" Problems: {problems}" if problems else ""))
    yield agui.text_end(message_id)
    yield agui.run_finished(run.thread_id, run.run_id, result={"elements": written, "rejected": len(rejected)})


if __name__ == "__main__":
    app.run(port_from_argv(8202))
