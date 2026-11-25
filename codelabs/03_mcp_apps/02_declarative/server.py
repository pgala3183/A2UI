"""MCP Apps, declarative mode: one generic view renders whatever spec the tool returns.

    python server.py            host page http://127.0.0.1:8302/  (MCP at /mcp)
    python server.py --stdio    for a real host

The view is a catalog renderer, not a dashboard. The server asks *its own*
model for a declarative spec (a flat element map from a catalog), validates
it, and returns it as structuredContent. The model key stays on the server;
the host's model never sees the spec, only the text summary.
Buttons in the spec call ``dashboard_action``, an app-only tool.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import mcp_app  # noqa: E402
from mcp import types  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from genui_common import bikes  # noqa: E402
from genui_common.elements import CATALOG_V1  # noqa: E402
from genui_common.llm import get_llm, last_user_text, reply_text, text, tool  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

VIEW_URI = "ui://bikes/spec-renderer.html"
network = bikes.Network()
mcp = FastMCP("bikes-declarative", json_response=True, log_level="WARNING")

SPEC_SYSTEM = f"""You design dashboards for a bike-share operations app. Reply with one JSON
object and nothing else: {{"root": "<id>", "elements": {{"<id>": {{"type", "props", "children"}}}}}}.
Buttons may use these actions: filter_attention, show_all.
{CATALOG_V1.prompt()}"""


def spec_respond(system: str, messages: list[dict]) -> str:
    """The server's scripted model: a spec for the question or the action."""
    view = "attention" if "filter_attention" in last_user_text(messages) else "all"
    rows = network.table() if view == "all" else [r for r in network.table() if r[3] != "balanced"]
    summary = network.summary()
    elements = {
        "dash": {"type": "Card", "props": {"title": "Stations needing attention" if view != "all" else "Network dashboard"},
                 "children": ["kpis", "chart", "table", "actions"]},
        "kpis": {"type": "Row", "props": {}, "children": ["m1", "m2", "m3"]},
        "m1": {"type": "Metric", "props": {"label": "Bikes docked", "value": f"{summary['bikes']} / {summary['capacity']}"}},
        "m2": {"type": "Metric", "props": {"label": "Rides today", "value": summary["rides_today"]}},
        "m3": {"type": "Metric", "props": {"label": "Need attention", "value": len(summary["needs_attention"])}},
        "chart": {"type": "BarChart", "props": {"title": "Bikes per station", "labels": [r[0] for r in rows],
                                                "values": [r[1] for r in rows]}},
        "table": {"type": "Table", "props": {"columns": ["Station", "Bikes", "Free docks", "Status"], "rows": rows}},
        "actions": {"type": "Row", "props": {}, "children": ["b1", "b2"]},
        "b1": {"type": "Button", "props": {"label": "Only stations needing attention", "action": "filter_attention"}},
        "b2": {"type": "Button", "props": {"label": "Show all", "action": "show_all", "variant": "secondary"}},
    }
    return json.dumps({"root": "dash", "elements": elements})


spec_llm = get_llm(spec_respond)


def generate_spec(request: str, attempts: int = 2) -> dict:
    """Ask the server's model for a spec; validation errors go back to it once."""
    messages = [{"role": "user", "content": request}]
    for _ in range(attempts):
        reply, _done = reply_text(spec_llm.stream(SPEC_SYSTEM, messages))
        try:
            spec = json.loads(reply)
            errors = CATALOG_V1.check_spec(spec)
        except ValueError as error:
            spec, errors = None, [f"not JSON: {error}"]
        if not errors:
            return spec
        messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": "Fix these errors: " + "; ".join(errors)}]
    raise ValueError("the model did not produce a valid spec")


def result(spec: dict, note: str) -> types.CallToolResult:
    titles = spec["elements"][spec["root"]]["props"].get("title", "")
    return types.CallToolResult(content=[types.TextContent(type="text", text=f"{note} Showing: {titles}.")],
                                structuredContent={"spec": spec})


@mcp.tool(meta={"ui": {"resourceUri": VIEW_URI}})
def render_dashboard(question: str) -> types.CallToolResult:
    """Build an interactive dashboard that answers a question about the bike-share network."""
    return result(generate_spec(question), "Dashboard generated.")


@mcp.tool(meta={"ui": {"visibility": ["app"]}})
def dashboard_action(action: str, params: dict | None = None) -> types.CallToolResult:
    """App-only: a button in the dashboard was pressed."""
    if action not in ("filter_attention", "show_all"):
        return types.CallToolResult(content=[types.TextContent(type="text", text=f"unknown action {action}")], isError=True)
    return result(generate_spec(f"[ui action] {action} {json.dumps(params or {})}"), f"Action {action} applied.")


@mcp.resource(VIEW_URI, name="spec_renderer_view", mime_type=mcp_app.MIME, meta=mcp_app.VIEW_META)
def spec_view() -> str:
    """A generic renderer for the catalog: the same view draws every spec."""
    return mcp_app.load_view(HERE / "view.html")


def host_respond(system: str, messages: list[dict]):
    return [text("Here is a live dashboard."), tool("render_dashboard", {"question": last_user_text(messages)})]


CONFIG = {"mode": "declarative", "title": "A generic view renders a generated spec",
          "prompts": ["Give me a dashboard for the whole network"],
          "note": "The view is a catalog renderer. The MCP server's own model writes a spec; the server validates it and returns it as structuredContent. Buttons call an app-only tool."}
app = mcp_app.http_app(mcp, HERE, host_respond, CONFIG)

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        mcp_app.run(app, port_from_argv(8302), "MCP Apps declarative")
