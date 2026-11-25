"""Offline tests for MCP Apps declarative mode: python -m pytest"""

import json

import pytest

import server  # first: sets sys.path
import mcp_app
from genui_common.elements import CATALOG_V1
from genui_common.llm import ScriptedLLM
from mcp_http import McpHttpClient


@pytest.fixture(scope="module")
def client():
    server.spec_llm = ScriptedLLM(server.spec_respond, delay=0)
    srv, base = mcp_app.start(server.app)
    c = McpHttpClient(base + "/mcp")
    c.initialize()
    yield c
    mcp_app.stop(srv)


def test_tools_and_visibility(client):
    tools = {t["name"]: t for t in client.request("tools/list")["tools"]}
    assert tools["render_dashboard"]["_meta"]["ui"]["resourceUri"] == server.VIEW_URI
    assert tools["dashboard_action"]["_meta"]["ui"]["visibility"] == ["app"]


def test_the_tool_returns_a_valid_spec(client):
    result = client.request("tools/call", {"name": "render_dashboard", "arguments": {"question": "network?"}})
    spec = result["structuredContent"]["spec"]
    assert CATALOG_V1.check_spec(spec) == []
    assert "Network dashboard" in result["content"][0]["text"]


def test_an_action_returns_a_new_spec(client):
    result = client.request("tools/call", {"name": "dashboard_action", "arguments": {"action": "filter_attention"}})
    spec = result["structuredContent"]["spec"]
    assert spec["elements"]["dash"]["props"]["title"] == "Stations needing attention"
    assert len(spec["elements"]["table"]["props"]["rows"]) == 3


def test_unknown_actions_are_errors(client):
    result = client.request("tools/call", {"name": "dashboard_action", "arguments": {"action": "drop_tables"}})
    assert result["isError"] is True


def test_invalid_specs_are_corrected_once():
    calls = []

    def flaky(system, messages):
        calls.append(messages)
        if len(calls) == 1:
            return json.dumps({"root": "x", "elements": {"x": {"type": "Carousel", "props": {}}}})
        return server.spec_respond(system, messages)

    server.spec_llm = ScriptedLLM(flaky, delay=0)
    try:
        spec = server.generate_spec("network?")
    finally:
        server.spec_llm = ScriptedLLM(server.spec_respond, delay=0)
    assert spec["root"] == "dash" and "Carousel" in calls[1][-1]["content"]


def test_the_view_inlines_the_kit(client):
    text = client.request("resources/read", {"uri": server.VIEW_URI})["contents"][0]["text"]
    assert "renderSpec" in text and "updateModelContext" in text
