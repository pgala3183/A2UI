"""Offline tests for A2UI mixed mode: python -m pytest"""

import json

import agent
import a2ui
import server
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from htmlframe import MIXED_CATALOG

server.llm = ScriptedLLM(agent.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def components(out):
    return [c for o in out if isinstance(o, dict) and "updateComponents" in o for c in o["updateComponents"]["components"]]


def test_layout_is_catalog_first_with_one_frame():
    comps = components(post(server.run, {"prompt": "desk"}))
    kinds = [c["component"] for c in comps]
    assert kinds.count("HtmlFrame") == 1
    assert len(kinds) > 10  # everything else is catalog
    assert all(MIXED_CATALOG.check(c) == [] for c in comps)


def test_a_second_frame_is_rejected():
    original = server.llm
    two = agent.respond("", []).replace('"sim"', '"sim"', 1) + "\n" + json.dumps(
        {"version": "v0.9", "updateComponents": {"surfaceId": agent.SURFACE, "components": [
            {"id": "sim2", "component": "HtmlFrame", "html": "<html><body>second frame</body></html>"}]}})
    server.llm = ScriptedLLM(lambda s, m: two, delay=0)
    try:
        out = post(server.run, {"prompt": "desk"})
    finally:
        server.llm = original
    assert out[-1][0] == "error" and "at most one HtmlFrame" in json.dumps(out[-1][1])


def act(name, source, **context):
    return {"version": "v0.9", "action": {"name": name, "surfaceId": agent.SURFACE, "sourceComponentId": source,
                                          "context": context}}


def test_frame_action_moves_bikes_and_updates_only_data():
    post(server.run, {"prompt": "desk"})
    before = server.network.get("mission")["bikes"]
    out = post(server.action, act("rebalance", "sim", **{"from": "ferry", "to": "mission", "count": 5}))
    assert {a2ui.kind(o) for o in out} == {"updateDataModel"}
    assert server.network.get("mission")["bikes"] == before + 5
    assert out[-1]["updateDataModel"]["value"].startswith("Moved 5 bikes")


def test_capacity_rules_hold_whatever_the_frame_sends():
    post(server.run, {"prompt": "desk"})
    out = post(server.action, act("rebalance", "sim", **{"from": "mission", "to": "ferry", "count": 50}))
    assert out[-1]["updateDataModel"]["value"].startswith("Not applied")


def test_actions_are_bound_to_their_source_component():
    post(server.run, {"prompt": "desk"})
    out = post(server.action, act("rebalance", "refresh", **{"from": "ferry", "to": "mission", "count": 1}))
    assert out[0][0] == "error"
    ok = post(server.action, act("refresh", "refresh"))
    assert ok[-1]["updateDataModel"]["value"].startswith("Numbers refreshed")
