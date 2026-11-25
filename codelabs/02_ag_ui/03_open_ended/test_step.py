"""Offline tests for AG-UI open-ended mode: python -m pytest"""

import json

import pytest

import agent
import server
from genui_common.llm import ScriptedLLM, text
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)


def run(messages, state=None):
    body = {"threadId": "t", "runId": "r", "state": state or {},
            "messages": [{"id": str(i), "role": "user", "content": m} for i, m in enumerate(messages)]}
    return list(server.run_agent(Request("POST", "/agent", {}, {}, json.dumps(body).encode())))


def customs(events, name):
    return [e["value"] for e in events if e["type"] == "CUSTOM" and e["name"] == name]


def test_html_is_sent_once_after_the_fence_closes():
    events = run(["calculator"])
    html = customs(events, "genui.html")
    assert len(html) == 1 and html[0]["html"].lstrip().startswith("<!doctype html>")
    position = next(i for i, e in enumerate(events) if e["type"] == "CUSTOM")
    assert events[position - 1]["type"] == "TEXT_MESSAGE_END"  # never inside an open text message


def test_initial_data_follows_the_document():
    data = customs(run(["calculator"]), "genui.data")
    assert data[0]["data"]["pricing"]["per_minute"] == 0.25


def test_a_document_that_breaks_policy_is_not_shipped():
    original = server.llm
    server.llm = ScriptedLLM(lambda s, m: [text("```html\n<html><script>fetch('/x')</script></html>\n```")], delay=0)
    try:
        events = run(["calculator"])
    finally:
        server.llm = original
    assert not customs(events, "genui.html")
    assert "fetch" in json.dumps(customs(events, "genui.html.rejected"))


def test_booking_runs_the_backend_tool_and_updates_the_frame():
    events = run(["calculator", '[ui action] book_ride {"minutes": 30, "ebike": false, "member": true, "cost": 1}'],
                 state={"artifact": "html_r"})
    result = json.loads(next(e for e in events if e["type"] == "TOOL_CALL_RESULT")["content"])
    assert result["price"] == 4.25  # (1 + 30 * 0.25) * 0.5, computed by the server
    assert customs(events, "genui.data")[0]["data"]["message"].startswith("Booked RIDE-")
    reply = "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "$4.25" in reply


def test_events_match_the_official_ag_ui_models():
    core = pytest.importorskip("ag_ui.core")
    from pydantic import TypeAdapter

    adapter = TypeAdapter(core.Event)
    for event in run(["calculator"]):
        adapter.validate_python(event)
