"""Offline tests for json-render declarative mode: python -m pytest"""

import json

import agent
import server
from genui_common import jsonpatch
from genui_common.llm import ScriptedLLM
from genui_common.testing import run_node_tests
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_stream_builds_a_valid_spec():
    out = post(server.run, {"prompt": "dashboard"})
    spec = {"root": None, "elements": {}, "state": {}}
    for event, op in out:
        if event == "patch":
            spec = jsonpatch.apply_op(spec, op)
    assert agent.CATALOG.check(spec) == [] and spec["root"] == "dash"
    assert out[-1] == ("note", {"elements": 8, "valid": True})


def test_the_root_paints_after_two_patches():
    patches = [op for e, op in post(server.run, {"prompt": "dashboard"}) if e == "patch"]
    assert patches[0]["path"] == "/root" and patches[1]["path"] == "/elements/dash"


def test_the_gate_refuses_what_the_catalog_does_not_allow():
    lines = [{"op": "add", "path": "/root", "value": "x"},
             {"op": "add", "path": "/elements/x", "value": {"type": "Script", "props": {"src": "evil.js"}}},
             {"op": "add", "path": "/elements/y", "value": {"type": "Button", "props": {"label": "Go"}, "on": {"press": {"action": "rm_rf"}}}},
             {"op": "add", "path": "/__proto__/x", "value": 1}]
    server.llm = ScriptedLLM(lambda s, m: "\n".join(json.dumps(o) for o in lines), delay=0)
    try:
        out = post(server.run, {"prompt": "x"})
    finally:
        server.llm = ScriptedLLM(agent.respond, delay=0)
    refused = [d for e, d in out if e == "refused"]
    assert len(refused) == 3
    assert "unknown component 'Script'" in refused[0]["errors"][0]
    assert "unknown action" in refused[1]["errors"][0]


def test_refresh_patches_state_only():
    post(server.run, {"prompt": "dashboard"})
    out = post(server.action, {"action": "refresh"})
    assert out and all(op["path"].startswith("/state/") for _, op in out)


def test_stream_compiler_and_bindings_in_node():
    run_node_tests(agent.HERE.parent / "_shared" / "tests" / "stream.test.mjs")
