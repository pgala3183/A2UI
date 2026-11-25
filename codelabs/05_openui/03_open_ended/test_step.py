"""Offline tests for OpenUI open-ended mode: python -m pytest"""

import json

import server  # first: sets sys.path
import openui
from genui_common import bikes
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from openui_parse import resolve

server.llm = ScriptedLLM(server.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_the_document_is_one_line_and_resolves_intact():
    out = post(server.run, {"prompt": "calculator"})
    assert [e for e, _ in out].count("line") == 3
    tree = resolve(server.session["gate"].program, server.LIBRARY)
    assert tree["props"]["document"] == bikes.TRIP_CALCULATOR_HTML
    assert tree["props"]["data"]["pricing"]["unlock"] == 1.0


def test_progress_is_reported_while_the_long_line_streams():
    server.llm = ScriptedLLM(server.respond, delay=0)
    out = post(server.run, {"prompt": "calculator"})
    pending = [d for e, d in out if e == "pending" and d["id"] == "doc"]
    assert len(pending) >= 3 and pending[-1]["chars"] > pending[0]["chars"]


def test_policy_blocks_a_bad_document_in_either_order():
    first_call = openui.StatementGate(server.LIBRARY, extra_check=openui.artifact_policy)
    assert first_call.offer('root = HtmlArtifact("x", doc)') == []
    assert "network" in first_call.offer('doc = "<script>fetch(1)</script>"')[0]
    first_doc = openui.StatementGate(server.LIBRARY, extra_check=openui.artifact_policy)
    assert first_doc.offer('doc = "<script>fetch(1)</script>"') == []  # just a string, so far
    assert "network" in first_doc.offer('root = HtmlArtifact("x", doc)')[0]


def test_booking_replaces_the_prices_statement():
    post(server.run, {"prompt": "calculator"})
    out = post(server.action, {"action": "book_ride", "source": "root", "params": {"minutes": 20, "ebike": True, "member": False}})
    line = out[0][1]["line"]
    assert line.startswith("prices = ") and "Booked: 20 min for $9.00" in line
    data = resolve(server.session["gate"].program, server.LIBRARY)["props"]["data"]
    assert data["message"].startswith("Booked")
