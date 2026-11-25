"""Offline tests for MCP Apps open-ended mode: python -m pytest"""

import pytest

import server  # first: sets sys.path
import mcp_app
from genui_common.llm import ScriptedLLM
from mcp_http import McpHttpClient


@pytest.fixture(scope="module")
def client():
    server.html_llm = ScriptedLLM(lambda s, m: server.bikes.TRIP_CALCULATOR_HTML, delay=0)
    srv, base = mcp_app.start(server.app)
    c = McpHttpClient(base + "/mcp")
    c.initialize()
    yield c
    mcp_app.stop(srv)


def test_the_resource_is_a_fixed_shell(client):
    text = client.request("resources/read", {"uri": server.VIEW_URI})["contents"][0]["text"]
    assert "mountGenerated" in text and "Trip cost" not in text  # no widget inside the resource


def test_the_widget_travels_in_structured_content(client):
    result = client.request("tools/call", {"name": "generate_widget", "arguments": {"request": "trip calculator"}})
    data = result["structuredContent"]
    assert data["html"].startswith("<!doctype html>") and data["data"]["pricing"]["unlock"] == 1.0
    assert "chars of HTML" in result["content"][0]["text"]  # the host's model gets a summary, not the code


def test_policy_violations_never_leave_the_server(client):
    server.html_llm = ScriptedLLM(lambda s, m: '<html><script src="https://evil.example/x.js"></script></html>', delay=0)
    try:
        result = client.request("tools/call", {"name": "generate_widget", "arguments": {"request": "x"}})
    finally:
        server.html_llm = ScriptedLLM(lambda s, m: server.bikes.TRIP_CALCULATOR_HTML, delay=0)
    assert result["isError"] is True and "content policy" in result["content"][0]["text"]


def test_booking_uses_the_server_price(client):
    result = client.request("tools/call", {"name": "book_ride", "arguments": {"minutes": 30, "ebike": True, "member": False}})
    assert result["structuredContent"]["price"] == 13.0  # 1 + 30 * (0.25 + 0.15)
    bad = client.request("tools/call", {"name": "book_ride", "arguments": {"minutes": 900, "ebike": True, "member": False}})
    assert bad["isError"] is True
