"""Offline tests for json-render open-ended mode: python -m pytest"""

import json

import agent
import server
from genui_common import bikes, jsonpatch
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from jr import PatchGate

server.llm = ScriptedLLM(agent.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_chunks_rebuild_the_exact_document():
    spec = {"root": None, "elements": {}, "state": {}}
    for event, op in post(server.run, {"prompt": "calculator"}):
        assert event == "patch"
        spec = jsonpatch.apply_op(spec, op)
    props = spec["elements"]["calc"]["props"]
    assert "".join(props["chunks"]) == bikes.TRIP_CALCULATOR_HTML and props["complete"] is True


def test_completion_is_refused_for_a_bad_document():
    gate = PatchGate(agent.CATALOG, extra_check=agent.html_policy)
    gate.offer({"op": "add", "path": "/root", "value": "x"})
    assert gate.offer({"op": "add", "path": "/elements/x", "value": {"type": "HtmlArtifact",
                                                                     "props": {"chunks": ['<script src="https://x.y/z.js">']}}}) == []
    errors = gate.offer({"op": "add", "path": "/elements/x/props/complete", "value": True})
    assert errors and "external" in errors[0]
    assert "complete" not in gate.spec["elements"]["x"]["props"]


def test_booking_answers_with_a_state_patch():
    post(server.run, {"prompt": "calculator"})
    out = post(server.action, {"action": "book_ride", "element": "calc", "params": {"minutes": 45, "ebike": False, "member": False}})
    assert out == [("patch", {"op": "add", "path": "/state/message", "value": "Booked: 45 min for $12.25 (server price)."})]


def test_actions_from_elsewhere_are_refused():
    out = post(server.action, {"action": "book_ride", "element": "other", "params": {"minutes": 45}})
    assert out[0][0] == "error"
