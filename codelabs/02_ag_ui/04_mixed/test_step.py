"""Offline tests for AG-UI mixed mode: python -m pytest"""

import json

import pytest

import agent
import server
from genui_common import bikes, jsonpatch
from genui_common.llm import ScriptedLLM
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)
CONFIRM = {"name": "confirm_rebalance", "description": "ask", "parameters": {"type": "object"}}


def run(messages, state=None):
    body = {"threadId": "t", "runId": "r", "state": state or {}, "messages": messages, "tools": [CONFIRM]}
    return list(server.run_agent(Request("POST", "/agent", {}, {}, json.dumps(body).encode())))


def replay(events, state=None):
    state = state or {}
    for e in events:
        if e["type"] == "STATE_SNAPSHOT":
            state = e["snapshot"]
        elif e["type"] == "STATE_DELTA":
            state = jsonpatch.apply_patch(state, e["delta"])
    return state


def user(i, content):
    return {"id": str(i), "role": "user", "content": content}


def test_first_run_splits_output_into_state_artifact_chat_and_a_render_tool():
    events = run([user(1, "Build me a rebalancing desk")])
    state = replay(events)
    assert state["ui"]["root"] == "desk" and agent.CATALOG.check_spec(state["ui"]) == []
    assert state["data"]["stations"][0]["id"] == "market"
    html = [e for e in events if e["type"] == "CUSTOM" and e["name"] == "genui.html"]
    assert len(html) == 1 and "html" not in json.dumps(state)  # the artifact is not in state
    chat = "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert chat.strip() == "Here is your rebalancing desk."
    assert [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"] == ["show_alert"]


def test_an_action_ends_the_run_on_the_frontend_tool():
    state = replay(run([user(1, "desk")]))
    events = run([user(1, "desk"), user(2, '[ui action] rebalance {"from": "ferry", "to": "mission", "count": 4}')], state)
    calls = [e for e in events if e["type"] == "TOOL_CALL_START"]
    assert [c["toolCallName"] for c in calls] == ["confirm_rebalance"]
    assert not [e for e in events if e["type"] == "TOOL_CALL_RESULT"]  # the page answers it
    assert events[-1]["type"] == "RUN_FINISHED"


def confirm_history(confirmed):
    plan = {"from": "ferry", "to": "mission", "count": 4}
    return [user(1, "desk"), user(2, "[ui action] rebalance " + json.dumps(plan)),
            {"id": "3", "role": "assistant", "content": "Please confirm this plan.",
             "toolCalls": [{"id": "call_1", "type": "function", "function": {"name": "confirm_rebalance", "arguments": json.dumps(plan)}}]},
            {"id": "4", "role": "tool", "toolCallId": "call_1", "content": json.dumps({"confirmed": confirmed, "plan": plan})}]


def test_confirmed_plan_runs_the_backend_tool_and_patches_state():
    server.network = bikes.Network()
    state = replay(run([user(1, "desk")]))
    events = run(confirm_history(True), state)
    assert [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"] == ["rebalance"]
    after = replay(events, state)
    mission = next(s for s in after["data"]["stations"] if s["id"] == "mission")
    assert mission["bikes"] == 4
    assert "Done: moved 4 bikes" in "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")


def test_cancelled_plan_moves_nothing():
    server.network = bikes.Network()
    state = replay(run([user(1, "desk")]))
    events = run(confirm_history(False), state)
    assert not [e for e in events if e["type"] == "TOOL_CALL_START"]
    assert server.network.get("mission")["bikes"] == 0


def test_events_match_the_official_ag_ui_models():
    core = pytest.importorskip("ag_ui.core")
    from pydantic import TypeAdapter

    adapter = TypeAdapter(core.Event)
    for event in run([user(1, "desk")]):
        adapter.validate_python(event)
