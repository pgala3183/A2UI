"""Offline tests for OpenUI mixed mode: python -m pytest"""

import json

import server  # first: sets sys.path
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from openui_parse import resolve

server.llm = ScriptedLLM(server.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def types(node, out):
    if isinstance(node, dict) and "type" in node:
        out.append(node["type"])
        for value in node.get("props", {}).values():
            types(value, out)
    elif isinstance(node, list):
        for item in node:
            types(item, out)
    return out


def test_library_first_with_one_artifact():
    out = post(server.run, {"prompt": "desk"})
    assert not [e for e, _ in out if e == "refused"] and out[-1][1]["unresolved"] == []
    found = types(resolve(server.session["gate"].program, server.LIBRARY), [])
    assert found.count("HtmlArtifact") == 1 and len(found) >= 8


def test_rebalance_resends_only_application_statements():
    post(server.run, {"prompt": "desk"})
    before = dict(server.session["gate"].program.statements)
    out = post(server.action, {"action": "rebalance", "source": "sim", "params": {"from": "ferry", "to": "mission", "count": 6}})
    ids = [d["line"].split(" =")[0] for e, d in out if e == "line"]
    assert ids == ["bikes", "need", "attention", "note", "simData"]
    after = server.session["gate"].program.statements
    assert after["simDoc"] == before["simDoc"] and after["sim"] == before["sim"]  # the iframe can stay
    assert len(after) == len(before)


def test_capacity_errors_become_a_note():
    post(server.run, {"prompt": "desk"})
    out = post(server.action, {"action": "rebalance", "source": "sim", "params": {"from": "mission", "to": "ferry", "count": 5}})
    note = next(d["line"] for e, d in out if e == "line" and d["line"].startswith("note"))
    assert "Not applied" in note


def test_actions_must_come_from_their_source():
    post(server.run, {"prompt": "desk"})
    assert post(server.action, {"action": "rebalance", "source": "button", "params": {}})[0][0] == "error"
    assert post(server.action, {"action": "refresh", "source": "button"})[-1][1]["line"].startswith("simData")
