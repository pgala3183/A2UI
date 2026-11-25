"""Harness, open-ended mode: render_html, behind a permission and a policy.

``render_html`` lets the model ship a whole HTML document. Two harness
mechanisms guard it:

* permission "ask": the loop pauses until the user approves the call
  (the same gate a coding harness uses before running a shell command);
* a content policy on the document, whose violations are error results.

The document declares the actions it may send back. A click inside it starts
a new turn only if its action was declared. ``send_to_view`` lets the model
push data into a view it rendered.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text, text, tool, tool_results  # noqa: E402
from genui_common.sandbox import check_html, inject_csp  # noqa: E402
from harness.loop import Harness  # noqa: E402
from harness.tools import Registry, ToolError, obj  # noqa: E402

ARTIFACTS: dict[str, str] = {}  # view id -> HTML with CSP, served by the web surface
S = {"type": "string"}
SYSTEM = ("You are the assistant of a bike-share app with a web surface. For interactive requests call "
          "render_html(view, title, html, actions): a complete HTML document with inline CSS/JS only, no network; "
          "it sends genui.send(name, payload) for the names in actions and reads genui.onData(fn). UI actions "
          "arrive as '[ui action] <name> <json>'. For book_ride, call quote_ride, then send_to_view with a message.")


def make_registry(network: bikes.Network) -> Registry:
    registry = Registry()

    @registry.add("render_html", "Show an interactive HTML document (needs the user's approval).",
                  obj(["view", "title", "html", "actions"], view=S, title=S, html=S,
                      actions={"type": "array", "items": {"type": "string", "pattern": "^[a-z_]+$"}}),
                  permission="ask")
    def render_html(view, title, html, actions):
        problems = check_html(html)
        if problems:
            raise ToolError("content policy: " + "; ".join(problems))
        ARTIFACTS[view] = inject_csp(html)
        url = f"/artifacts/{view}.html"
        event = {"type": "ui", "kind": "html", "view": view, "title": title, "html": html,
                 "artifact_url": url, "actions": actions, "placement": "standalone"}
        return f"rendered {title} as view {view} (terminal users: {url})", [event]

    @registry.add("quote_ride", "The official price of a ride.",
                  obj(["minutes", "ebike", "member"], minutes={"type": "number", "minimum": 5, "maximum": 180},
                      ebike={"type": "boolean"}, member={"type": "boolean"}))
    def quote_ride(minutes, ebike, member):
        return {"minutes": minutes, "price": network.ride_cost(minutes, ebike, member)}

    @registry.add("send_to_view", "Push data into a view you rendered.", obj(["view", "data"], view=S, data={"type": "object"}))
    def send_to_view(view, data):
        if view not in ARTIFACTS:
            raise ToolError(f"no view {view}")
        return f"sent to {view}", [{"type": "ui", "kind": "data", "view": view, "data": data}]

    return registry


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if results:
        content = results[0]["content"]
        if results[0].get("is_error"):
            return [text("Understood, I will not show it.")]
        if '"price"' in content:
            quote = json.loads(content)
            message = f"Booked: {quote['minutes']} min for ${quote['price']:.2f} (server price)."
            return [tool("send_to_view", {"view": "calc", "data": {"message": message}}), text(message)]
        if content.startswith("rendered"):
            return [text("The calculator is on the web surface. Book a ride from it when you are ready.")]
        return []
    prompt = last_user_text(messages)
    marker = prompt.rfind("[ui action] book_ride")
    if marker >= 0:
        payload = json.loads(prompt[marker:].split(" ", 3)[3].rsplit(" (from view", 1)[0])
        return [tool("quote_ride", {k: payload[k] for k in ("minutes", "ebike", "member")})]
    return [text("I will build an interactive calculator."),
            tool("render_html", {"view": "calc", "title": "Trip cost calculator", "html": bikes.TRIP_CALCULATOR_HTML,
                                 "actions": ["book_ride"]})]


def make_harness(llm=None) -> Harness:
    return Harness(llm or get_llm(respond), SYSTEM, make_registry(bikes.Network()))
