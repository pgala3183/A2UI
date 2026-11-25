"""MCP Apps, mixed mode: catalog components and a generated region in one view.

    python server.py            host page http://127.0.0.1:8304/  (MCP at /mcp)
    python server.py --stdio    for a real host

``ops_desk`` returns structuredContent with three parts:
  spec       catalog elements (validated), one of them a GeneratedView
  generated  {artifact id: HTML} written by the server's model (checked)
  stations   the data both halves render
``rebalance`` is app-only: the simulator inside the nested frame asks for it,
the view relays it, the server checks capacity and answers with new data.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import mcp_app  # noqa: E402
from mcp import types  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from genui_common import bikes  # noqa: E402
from genui_common.elements import CATALOG_V1, GENERATED_VIEW  # noqa: E402
from genui_common.llm import get_llm, last_user_text, reply_text, text, tool  # noqa: E402
from genui_common.sandbox import check_html  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

VIEW_URI = "ui://bikes/ops-desk.html"
CATALOG = CATALOG_V1.with_types(GeneratedView=GENERATED_VIEW)
network = bikes.Network()
mcp = FastMCP("bikes-mixed", json_response=True, log_level="WARNING")

html_llm = get_llm(lambda system, messages: bikes.REBALANCE_SIMULATOR_HTML)


def stations() -> list[dict]:
    return [{"id": s["id"], "name": s["name"], "bikes": s["bikes"], "capacity": s["capacity"]} for s in network.stations]


def spec() -> dict:
    """Catalog first: everything here is a validated catalog element except one region."""
    summary = network.summary()
    names = ", ".join(network.get(i)["name"] for i in summary["needs_attention"]) or "none"
    return {"root": "desk", "elements": {
        "desk": {"type": "Column", "props": {}, "children": ["header", "sim", "footer"]},
        "header": {"type": "Card", "props": {"title": "Rebalancing desk"}, "children": ["kpis", "attention"]},
        "kpis": {"type": "Row", "props": {}, "children": ["m1", "m2"]},
        "m1": {"type": "Metric", "props": {"label": "Bikes docked", "value": f"{summary['bikes']} / {summary['capacity']}"}},
        "m2": {"type": "Metric", "props": {"label": "Need attention", "value": len(summary["needs_attention"])}},
        "attention": {"type": "Text", "props": {"text": f"Needs attention: {names}", "variant": "caption"}},
        "sim": {"type": "GeneratedView", "props": {"artifact": "simulator", "height": 250}},
        "footer": {"type": "Row", "props": {}, "children": ["ask"]},
        "ask": {"type": "Button", "props": {"label": "Ask the assistant for a plan", "action": "ask_plan"}},
    }}


def desk(message: str) -> types.CallToolResult:
    s = spec()
    assert CATALOG.check_spec(s) == []
    html, _ = reply_text(html_llm.stream("Write the rebalancing simulator.", [{"role": "user", "content": "simulator"}]))
    problems = check_html(html)
    if problems:
        return types.CallToolResult(content=[types.TextContent(type="text", text="; ".join(problems))], isError=True)
    text_summary = f"{message} " + "; ".join(f"{x['name']} {x['bikes']}/{x['capacity']}" for x in stations())
    return types.CallToolResult(content=[types.TextContent(type="text", text=text_summary)],
                                structuredContent={"spec": s, "generated": {"simulator": html}, "stations": stations(),
                                                   "message": message})


@mcp.tool(meta={"ui": {"resourceUri": VIEW_URI}})
def ops_desk() -> types.CallToolResult:
    """Open the interactive rebalancing desk for the bike-share network."""
    return desk("Rebalancing desk opened.")


@mcp.tool(meta={"ui": {"visibility": ["app"]}})
def rebalance(source: str, target: str, count: int) -> types.CallToolResult:
    """App-only: move bikes between stations (capacity is enforced here)."""
    result = network.rebalance(source, target, count)
    if not result["ok"]:
        return types.CallToolResult(content=[types.TextContent(type="text", text=result["error"])], isError=True)
    return desk(f"Moved {result['moved']} bikes from {result['from']} to {result['to']}.")


@mcp.resource(VIEW_URI, name="ops_desk_view", mime_type=mcp_app.MIME, meta=mcp_app.VIEW_META)
def desk_view() -> str:
    return mcp_app.load_view(HERE / "view.html")


def host_respond(system: str, messages: list[dict]):
    prompt = last_user_text(messages)
    if "plan" in prompt.lower() and "[app context" in prompt:
        return [text("Based on what the desk shows: move 6 bikes from Ferry Building to Mission & 16th, "
                     "then 5 from SJSU Student Union to Market St & 4th.")]
    return [text("Opening the rebalancing desk."), tool("ops_desk", {})]


CONFIG = {"mode": "mixed", "title": "Catalog components and a generated region in one MCP App",
          "prompts": ["Open the rebalancing desk"],
          "note": "One view, two halves: catalog elements from a validated spec, and a simulator written by the server's model in a nested sandbox. The simulator's actions go through an app-only tool."}
app = mcp_app.http_app(mcp, HERE, host_respond, CONFIG)

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        mcp_app.run(app, port_from_argv(8304), "MCP Apps mixed")
