"""Offline tests for MCP Apps mixed mode: python -m pytest"""

import pytest

import server  # first: sets sys.path
import mcp_app
from genui_common import bikes
from genui_common.llm import ScriptedLLM
from mcp_http import McpHttpClient


@pytest.fixture(scope="module")
def client():
    server.html_llm = ScriptedLLM(lambda s, m: bikes.REBALANCE_SIMULATOR_HTML, delay=0)
    srv, base = mcp_app.start(server.app)
    c = McpHttpClient(base + "/mcp")
    c.initialize()
    yield c
    mcp_app.stop(srv)


def test_structured_content_has_spec_generated_region_and_data(client):
    data = client.request("tools/call", {"name": "ops_desk", "arguments": {}})["structuredContent"]
    assert server.CATALOG.check_spec(data["spec"]) == []
    types = [e["type"] for e in data["spec"]["elements"].values()]
    assert types.count("GeneratedView") == 1 and len(types) > 6
    assert set(data["generated"]) == {"simulator"} and len(data["stations"]) == 5


def test_rebalance_is_app_only_and_enforces_capacity(client):
    tools = {t["name"]: t for t in client.request("tools/list")["tools"]}
    assert tools["rebalance"]["_meta"]["ui"]["visibility"] == ["app"]
    bad = client.request("tools/call", {"name": "rebalance", "arguments": {"source": "mission", "target": "ferry", "count": 3}})
    assert bad["isError"] is True
    ok = client.request("tools/call", {"name": "rebalance", "arguments": {"source": "ferry", "target": "mission", "count": 6}})
    assert ok["structuredContent"]["message"].startswith("Moved 6 bikes")
    mission = next(s for s in ok["structuredContent"]["stations"] if s["id"] == "mission")
    assert mission["bikes"] == 6


def test_host_model_uses_app_context():
    llm = ScriptedLLM(server.host_respond, delay=0)
    reply = list(llm.stream("", [{"role": "user", "content": "[app context: desk]\nSuggest a rebalancing plan"}]))[-1]
    assert reply["content"][0]["type"] == "text" and "Ferry Building" in reply["content"][0]["text"]
