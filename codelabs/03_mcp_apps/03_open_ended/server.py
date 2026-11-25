"""MCP Apps, open-ended mode: the server's model writes the HTML; the view is a shell.

    python server.py            host page http://127.0.0.1:8303/  (MCP at /mcp)
    python server.py --stdio    for a real host

Why not a new ui:// resource per answer? The tool declares its resourceUri
up front, and hosts may fetch and cache that resource before any call. So
the resource is a small, fixed shell, and the generated document travels in
structuredContent. The shell mounts it in a *nested* sandbox:
host page -> view iframe -> generated iframe. Two boundaries.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import mcp_app  # noqa: E402
from mcp import types  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text, reply_text, text, tool  # noqa: E402
from genui_common.sandbox import check_html  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

VIEW_URI = "ui://bikes/generated-shell.html"
network = bikes.Network()
references = itertools.count(501)
mcp = FastMCP("bikes-open-ended", json_response=True, log_level="WARNING")

HTML_SYSTEM = """Write one complete HTML document for the user's request and nothing else.
Inline CSS and JS only; no external URLs, no network, no storage. The document runs in a
sandboxed iframe: genui.onData(fn) gives it {pricing, message}; genui.send(name, payload)
sends an action. A trip calculator sends "book_ride" with {minutes, ebike, member, cost}."""

html_llm = get_llm(lambda system, messages: bikes.TRIP_CALCULATOR_HTML)


def generate_html(request: str) -> str:
    html, _done = reply_text(html_llm.stream(HTML_SYSTEM, [{"role": "user", "content": request}]))
    html = html.strip().removeprefix("```html").removesuffix("```").strip()
    problems = check_html(html)
    if problems:
        raise ValueError("generated HTML failed the content policy: " + "; ".join(problems))
    return html


@mcp.tool(meta={"ui": {"resourceUri": VIEW_URI}})
def generate_widget(request: str) -> types.CallToolResult:
    """Generate a small interactive widget (HTML) for the user's request."""
    html = generate_html(request)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Generated an interactive widget ({len(html)} chars of HTML).")],
        structuredContent={"title": "Trip cost calculator", "html": html, "data": {"pricing": network.pricing}})


@mcp.tool(meta={"ui": {"visibility": ["app"]}})
def book_ride(minutes: float, ebike: bool, member: bool) -> types.CallToolResult:
    """App-only: book a ride at the server's price."""
    if not 5 <= minutes <= 180:
        return types.CallToolResult(content=[types.TextContent(type="text", text="minutes must be 5 to 180")], isError=True)
    price = network.ride_cost(minutes, ebike, member)
    reference = f"RIDE-{next(references)}"
    message = f"Booked {reference}: {int(minutes)} min for ${price:.2f} (server price)."
    return types.CallToolResult(content=[types.TextContent(type="text", text=message)],
                                structuredContent={"reference": reference, "price": price, "message": message})


@mcp.resource(VIEW_URI, name="generated_shell_view", mime_type=mcp_app.MIME, meta=mcp_app.VIEW_META)
def shell_view() -> str:
    return mcp_app.load_view(HERE / "view.html")


def host_respond(system: str, messages: list[dict]):
    prompt = last_user_text(messages)
    if "I booked" in prompt:
        return [text("Noted. Your ride is booked; the price came from the server, not from the widget.")]
    return [text("Generating a widget for that."), tool("generate_widget", {"request": prompt})]


CONFIG = {"mode": "open-ended", "title": "Generated HTML inside an MCP App",
          "prompts": ["Make me an interactive trip-cost calculator"],
          "note": "The ui:// resource is a fixed shell. The server's model writes the widget, the server checks it, and the shell mounts it in a nested sandbox: host -> view -> generated frame."}
app = mcp_app.http_app(mcp, HERE, host_respond, CONFIG)

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        mcp_app.run(app, port_from_argv(8303), "MCP Apps open-ended")
