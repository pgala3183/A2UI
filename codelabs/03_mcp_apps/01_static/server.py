"""MCP Apps, static mode: a tool whose result comes with a pre-built view.

    python server.py            host page http://127.0.0.1:8301/  (MCP at /mcp)
    python server.py --stdio    for a real host (Claude Desktop, Goose, VS Code...)

The view is hand-written HTML, fixed at build time: a static component. The
model (in the host) only decides to call the tool and with which station.
The server stays an ordinary FastMCP server; the UI is two pieces of metadata.
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
from genui_common.llm import last_user_text, text, tool  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

VIEW_URI = "ui://bikes/station-dashboard.html"
network = bikes.Network()
mcp = FastMCP("bikes-static", json_response=True, log_level="WARNING")


@mcp.tool(meta={"ui": {"resourceUri": VIEW_URI}})
def station_dashboard(station_id: str = "market") -> types.CallToolResult:
    """Live dashboard for one bike-share station (ids: market, ferry, caltrain, mission, sjsu)."""
    v = network.view(station_id)
    return types.CallToolResult(
        # content: what the model reads, and what a host without UI support shows
        content=[types.TextContent(type="text", text=f"{v['name']}: {v['bikes']}/{v['capacity']} bikes ({v['status']}).")],
        # structuredContent: what the view renders
        structuredContent={**v, "hours": bikes.HOURS},
    )


@mcp.resource(VIEW_URI, name="station_dashboard_view", mime_type=mcp_app.MIME, meta=mcp_app.VIEW_META)
def station_view() -> str:
    """The hand-written view. It has no data of its own: data arrives over postMessage."""
    return mcp_app.load_view(HERE / "view.html")


def host_respond(system: str, messages: list[dict]):
    """The host's scripted model: call the tool for a station, or answer the app's question."""
    prompt = last_user_text(messages).lower()
    if prompt.startswith("why is"):
        return [text("Commuters empty it in the 8 am peak and few bikes come back before 5 pm. "
                     "A van run before 7 am fixes it.")]
    station = next((s for s in bikes.STATIONS if s["id"] in prompt or s["name"].lower() in prompt), bikes.STATIONS[0])
    return [text(f"Opening the {station['name']} dashboard."), tool("station_dashboard", {"station_id": station["id"]})]


CONFIG = {"mode": "static", "title": "A pre-built view in a ui:// resource",
          "prompts": ["Show me the Market St station", "Show me the Ferry Building station"],
          "note": "The tool's _meta.ui.resourceUri points at a hand-written HTML view. The host reads it, sandboxes it, and hands it the tool result over postMessage."}
app = mcp_app.http_app(mcp, HERE, host_respond, CONFIG)

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        mcp_app.run(app, port_from_argv(8301), "MCP Apps static")
