"""Offline tests for harness mixed mode: python -m pytest"""

import agent
from genui_common import bikes
from genui_common.llm import ScriptedLLM


def harness():
    return agent.make_harness(ScriptedLLM(agent.respond, delay=0))


def built():
    h = harness()
    events = list(h.ask("Build me a rebalancing desk"))
    return h, events


def test_one_turn_uses_static_declarative_and_open_ended_ui():
    _, events = built()
    kinds = [(e["kind"], e.get("component")) for e in events if e["type"] == "ui"]
    assert kinds == [("component", "Alert"), ("html", None), ("spec", None), ("data", None)]
    spec = next(e for e in events if e["type"] == "ui" and e["kind"] == "spec")["spec"]
    assert agent.CATALOG.check_spec(spec) == []


def test_views_declare_their_actions():
    h, _ = built()
    assert h.allowed_actions == {"sim": {"rebalance"}, "desk": {"refresh"}}


def test_rendering_runs_but_the_side_effect_waits_for_approval():
    h, _ = built()
    events = list(h.ui_action("sim", "rebalance", {"from": "ferry", "to": "mission", "count": 6}))
    assert events[-1]["type"] == "permission_request" and events[-1]["name"] == "rebalance"
    stations = h.registry.get("query_stations").fn()["stations"]
    assert next(s for s in stations if s["id"] == "mission")["bikes"] == 0  # nothing moved yet


def test_approval_moves_bikes_and_rerenders_both_halves():
    h, _ = built()
    request = list(h.ui_action("sim", "rebalance", {"from": "ferry", "to": "mission", "count": 6}))[-1]
    events = list(h.resume(request["id"], True))
    spec = next(e for e in events if e["type"] == "ui" and e["kind"] == "spec")["spec"]
    assert spec["elements"]["m2"]["props"]["value"] == 1
    data = next(e for e in events if e["type"] == "ui" and e["kind"] == "data")["data"]
    assert data["message"] == "Moved 6 bikes from Ferry Building to Mission & 16th."
    mission = next(s for s in data["stations"] if s["id"] == "mission")
    assert mission["bikes"] == 6


def test_denial_moves_nothing():
    h, _ = built()
    request = list(h.ui_action("sim", "rebalance", {"from": "ferry", "to": "mission", "count": 6}))[-1]
    events = list(h.resume(request["id"], False))
    assert "Nothing moved." in "".join(e["text"] for e in events if e["type"] == "text")


def test_render_ui_refuses_a_view_without_its_artifact():
    agent.ARTIFACTS.clear()
    tool = agent.make_registry(bikes.Network()).get("render_ui")
    content, events, is_error = tool.execute({"view": "desk", "spec": agent.desk([])})
    assert is_error and "call render_html first" in content
