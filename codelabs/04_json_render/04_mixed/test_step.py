"""Offline tests for json-render mixed mode: python -m pytest"""

import json

import agent
import server
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from render_text import render_text

server.llm = ScriptedLLM(agent.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_spec_is_catalog_first_with_one_artifact():
    out = post(server.run, {"prompt": "desk"})
    assert not [o for o in out if o[0] == "refused"]
    spec = server.session["gate"].spec
    types = [e["type"] for e in spec["elements"].values()]
    assert types.count("HtmlArtifact") == 1 and len(types) >= 8
    assert agent.CATALOG.check(spec) == []


def test_set_state_is_declared_on_the_toggle_and_never_sent_to_the_server():
    post(server.run, {"prompt": "desk"})
    toggle = server.session["gate"].spec["elements"]["toggle"]
    assert toggle["on"]["press"]["action"] == "setState"
    assert post(server.action, {"action": "setState", "element": "toggle", "params": {}})[0][0] == "error"


def test_rebalance_from_the_artifact_patches_state():
    post(server.run, {"prompt": "desk"})
    out = post(server.action, {"action": "rebalance", "element": "sim", "params": {"from": "ferry", "to": "mission", "count": 6}})
    paths = {op["path"] for _, op in out}
    assert all(p.startswith("/state/") for p in paths)
    assert "/state/message" in paths and server.session["gate"].spec["state"]["summary"]["attention"] == 1


def test_rebalance_from_a_catalog_element_is_refused():
    post(server.run, {"prompt": "desk"})
    assert post(server.action, {"action": "rebalance", "element": "toggle", "params": {}})[0][0] == "error"


def test_terminal_renderer_resolves_state_and_degrades_the_artifact():
    post(server.run, {"prompt": "desk"})
    text = render_text(server.session["gate"].spec)
    assert "Bikes docked: 49 / 100" in text
    assert "[interactive: Rebalancing simulator" in text
    assert "(Table table hidden)" in text  # visible is bound to /ui/showTable = false
