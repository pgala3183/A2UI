"""Offline tests for A2UI open-ended mode: python -m pytest"""

import json

import agent
import a2ui
import server
from genui_common import bikes
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from htmlframe import OPEN_CATALOG

server.llm = ScriptedLLM(agent.respond, delay=0)
server.PEAK_DELAY = 0


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_the_open_catalog_has_one_component():
    assert list(OPEN_CATALOG.components) == ["HtmlFrame"]
    assert "HtmlFrame(html, title?, height?)" in agent.SYSTEM


def test_run_sends_one_html_frame_then_server_data():
    out = [o for o in post(server.run, {"prompt": "calculator"}) if isinstance(o, dict)]
    kinds = [a2ui.kind(o) for o in out]
    assert kinds[0] in ("createSurface", "deleteSurface")
    frame = next(o for o in out if a2ui.kind(o) == "updateComponents")["updateComponents"]["components"]
    assert len(frame) == 1 and frame[0]["component"] == "HtmlFrame"
    paths = [o["updateDataModel"]["path"] for o in out if a2ui.kind(o) == "updateDataModel"]
    assert paths == ["/pricing", "/pricing/per_minute", "/message"]


def test_policy_blocks_network_and_external_scripts():
    bad = {"id": "root", "component": "HtmlFrame", "html": '<html><script src="https://x.y/z.js"></script></html>'}
    assert any("external" in p for p in OPEN_CATALOG.check(bad))
    bad["html"] = "<html><script>fetch('/x')</script></html>"
    assert any("fetch" in p for p in OPEN_CATALOG.check(bad))
    good = {"id": "root", "component": "HtmlFrame", "html": bikes.TRIP_CALCULATOR_HTML}
    assert OPEN_CATALOG.check(good) == []


def booking(**context):
    return {"version": "v0.9", "action": {"name": "book_ride", "surfaceId": agent.SURFACE,
                                          "sourceComponentId": "root", "context": context}}


def test_booking_uses_the_server_price_not_the_frame_price():
    post(server.run, {"prompt": "calculator"})  # sets peak pricing: 0.30/min
    out = post(server.action, booking(minutes=40, ebike=True, member=False, cost=1.0))
    message = out[0]["updateDataModel"]["value"]
    assert message.startswith("Booked: 40 min e-bike ride for $19.00")
    assert "page showed $1.00" in message


def test_bad_booking_is_answered_not_executed():
    post(server.run, {"prompt": "calculator"})
    out = post(server.action, booking(minutes=999, ebike="yes", member=False))
    assert out[0]["updateDataModel"]["value"].startswith("Not booked")
