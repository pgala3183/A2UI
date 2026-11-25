"""Offline tests for AG-UI declarative mode: python -m pytest"""

import json

import pytest

import agent
import server
from genui_common import jsonpatch
from genui_common.llm import ScriptedLLM
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)


def run(state, *texts):
    body = {"threadId": "t", "runId": "r", "state": state,
            "messages": [{"id": str(i), "role": "user", "content": t} for i, t in enumerate(texts)]}
    return list(server.run_agent(Request("POST", "/agent", {}, {}, json.dumps(body).encode())))


def replay(events, state=None):
    state = state or {}
    for e in events:
        if e["type"] == "STATE_SNAPSHOT":
            state = e["snapshot"]
        elif e["type"] == "STATE_DELTA":
            state = jsonpatch.apply_patch(state, e["delta"])
    return state


def test_first_run_is_a_snapshot_then_one_delta_per_element():
    events = run({}, "Build me a dashboard")
    kinds = [e["type"] for e in events]
    assert kinds.count("STATE_SNAPSHOT") == 1
    assert kinds.count("STATE_DELTA") == len(agent.elements())
    state = replay(events)
    assert state["ui"]["root"] == "dash"
    assert agent.CATALOG.check_spec(state["ui"]) == []


def test_action_run_patches_only_what_changed():
    state = replay(run({}, "Build me a dashboard"))
    events = run(state, "Build me a dashboard", "[ui action] filter_attention {}")
    assert "STATE_SNAPSHOT" not in [e["type"] for e in events]
    paths = [op["path"] for e in events if e["type"] == "STATE_DELTA" for op in e["delta"]]
    assert all(p.startswith(("/ui/elements/dash", "/ui/elements/chart", "/ui/elements/table")) for p in paths)
    after = replay(events, state)
    assert after["ui"]["elements"]["dash"]["props"]["title"] == "Stations needing attention"
    assert len(after["ui"]["elements"]["table"]["props"]["rows"]) == 3


def test_invalid_elements_are_rejected_not_patched():
    original = server.llm
    server.llm = ScriptedLLM(lambda s, m: '{"id": "dash", "type": "PieChart", "props": {}}\n'
                                          '{"id": "x", "type": "Text", "props": {"text": 5}}', delay=0)
    try:
        events = run({}, "anything")
    finally:
        server.llm = original
    rejected = [e for e in events if e["type"] == "CUSTOM" and e["name"] == "ui.rejected"]
    assert len(rejected) == 2 and "PieChart" in json.dumps(rejected[0])
    assert not [e for e in events if e["type"] == "STATE_DELTA"]


def test_a_tampered_state_is_replaced():
    events = run({"ui": {"root": "x", "elements": {"x": {"type": "Script", "props": {}}}}}, "Build me a dashboard")
    assert events[1]["type"] == "STATE_SNAPSHOT" and events[1]["snapshot"] == server.EMPTY


def test_events_match_the_official_ag_ui_models():
    core = pytest.importorskip("ag_ui.core")
    from pydantic import TypeAdapter

    adapter = TypeAdapter(core.Event)
    for event in run({}, "Build me a dashboard"):
        adapter.validate_python(event)
