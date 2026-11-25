"""Offline tests for MCP Apps static mode: python -m pytest

A real FastMCP server is started on a free port; the tests speak MCP to it.
"""

import asyncio

import pytest

import server  # first: it puts common/ and _shared/ on sys.path
import mcp_app
from genui_common.llm import ScriptedLLM
from mcp_http import McpHttpClient


@pytest.fixture(scope="module")
def url():
    server.app.state.host_llm["llm"] = ScriptedLLM(server.host_respond, delay=0)
    srv, base = mcp_app.start(server.app)
    yield base
    mcp_app.stop(srv)


@pytest.fixture()
def client(url):
    c = McpHttpClient(url + "/mcp")
    c.initialize()
    return c


def test_tool_points_at_a_ui_resource(client):
    tool = next(t for t in client.request("tools/list")["tools"] if t["name"] == "station_dashboard")
    assert tool["_meta"]["ui"]["resourceUri"] == server.VIEW_URI


def test_resource_is_an_mcp_app_html_document(client):
    content = client.request("resources/read", {"uri": server.VIEW_URI})["contents"][0]
    assert content["mimeType"] == "text/html;profile=mcp-app"
    assert content["_meta"]["ui"]["csp"] == {"connectDomains": [], "resourceDomains": []}
    assert "window.viewKit" in content["text"] and "<!--VIEW_KIT-->" not in content["text"]


def test_result_has_text_for_the_model_and_data_for_the_view(client):
    result = client.request("tools/call", {"name": "station_dashboard", "arguments": {"station_id": "ferry"}})
    assert result["content"][0]["text"].startswith("Ferry Building: 21/23 bikes")
    assert result["structuredContent"]["hourly"] and result["structuredContent"]["status"] == "full soon"


def test_the_host_model_picks_the_tool_and_answers_app_messages():
    llm = ScriptedLLM(server.host_respond, delay=0)
    done = list(llm.stream("", [{"role": "user", "content": "Show me the Ferry Building station"}]))[-1]
    assert done["content"][1]["input"] == {"station_id": "ferry"}
    done = list(llm.stream("", [{"role": "user", "content": "Why is Ferry Building full soon?"}]))[-1]
    assert done["content"][0]["type"] == "text"


def test_official_mcp_client_sees_the_same_thing(url):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async def go():
        async with streamable_http_client(url + "/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool = next(t for t in tools.tools if t.name == "station_dashboard")
                result = await session.call_tool("station_dashboard", {"station_id": "sjsu"})
                return tool.meta, result.structuredContent

    meta, data = asyncio.run(go())
    assert meta["ui"]["resourceUri"] == server.VIEW_URI and data["name"] == "SJSU Student Union"
