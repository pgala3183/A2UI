"""Harness, mixed mode: every kind of generative UI in one agent loop.

    show_alert     static: a pre-built component
    render_ui      declarative: a validated spec; one GeneratedView element
    render_html    open-ended: the simulator, embedded in that GeneratedView
    send_to_view   data into a rendered view
    rebalance      a side effect: permission "ask", so it waits for the user

Rendering is allowed (it is sandboxed and checked); changing the world is
not, until the user says yes. UI actions from the spec's button and from the
simulator both come back as turns, and only if the view declared them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.elements import CATALOG_V1, GENERATED_VIEW  # noqa: E402
from genui_common.llm import get_llm, last_user_text, text, tool, tool_results  # noqa: E402
from genui_common.sandbox import check_html, inject_csp  # noqa: E402
from harness.loop import Harness  # noqa: E402
from harness.tools import Registry, ToolError, obj  # noqa: E402

CATALOG = CATALOG_V1.with_types(GeneratedView=GENERATED_VIEW)
ARTIFACTS: dict[str, str] = {}
S = {"type": "string"}
SYSTEM = ("You run the rebalancing desk of a bike-share network. Prefer render_ui (catalog elements) for "
          "everything; embed one interactive simulator with render_html(placement='embedded') and a "
          "GeneratedView that names it. Push station data into it with send_to_view. Moving bikes needs "
          "rebalance, which the user must approve. UI actions arrive as '[ui action] <name> <json>'.\n"
          + CATALOG.prompt())


def stations_of(network):
    return [{k: s[k] for k in ("id", "name", "bikes", "capacity")} | {"status": bikes.status(s)} for s in network.stations]


def make_registry(network: bikes.Network) -> Registry:
    registry = Registry()

    @registry.add("query_stations", "Read live numbers for every station.", obj())
    def query_stations():
        return {"stations": stations_of(network)}

    @registry.add("show_alert", "Show an alert banner.", obj(["level", "text"], level={"enum": ["info", "warning", "success"]}, text=S))
    def show_alert(level, text):
        return "displayed alert", [{"type": "ui", "kind": "component", "view": "alert", "component": "Alert",
                                    "props": {"level": level, "text": text}}]

    @registry.add("render_html", "Render an interactive HTML document.",
                  obj(["view", "title", "html", "actions"], view=S, title=S, html=S, placement={"enum": ["standalone", "embedded"]},
                      actions={"type": "array", "items": {"type": "string"}}))
    def render_html(view, title, html, actions, placement="standalone"):
        problems = check_html(html)
        if problems:
            raise ToolError("content policy: " + "; ".join(problems))
        ARTIFACTS[view] = inject_csp(html)
        return f"rendered {title} as {view}", [{"type": "ui", "kind": "html", "view": view, "title": title, "html": html,
                                                "artifact_url": f"/artifacts/{view}.html", "actions": actions,
                                                "placement": placement}]

    @registry.add("render_ui", "Render a declarative spec.", obj(["view", "spec"], view=S, spec={"type": "object"}))
    def render_ui(view, spec):
        errors = CATALOG.check_spec(spec)
        missing = [e["props"]["artifact"] for e in spec.get("elements", {}).values()
                   if e.get("type") == "GeneratedView" and e["props"]["artifact"] not in ARTIFACTS]
        if errors or missing:
            raise ToolError("invalid spec: " + "; ".join(errors + [f"no artifact {m}; call render_html first" for m in missing]))
        actions = sorted({e["props"]["action"] for e in spec["elements"].values() if e["type"] == "Button"})
        return f"rendered {view}", [{"type": "ui", "kind": "spec", "view": view, "spec": spec, "actions": actions}]

    @registry.add("send_to_view", "Push data into a rendered view.", obj(["view", "data"], view=S, data={"type": "object"}))
    def send_to_view(view, data):
        return f"sent to {view}", [{"type": "ui", "kind": "data", "view": view, "data": data}]

    @registry.add("rebalance", "Move bikes between stations. Needs the user's approval.",
                  obj(["source", "target", "count"], source=S, target=S, count={"type": "integer", "minimum": 1}),
                  permission="ask")
    def rebalance(source, target, count):
        result = network.rebalance(source, target, count)
        if not result["ok"]:
            raise ToolError(result["error"])
        return {**result, "stations": stations_of(network)}

    return registry


def desk(stations: list[dict]) -> dict:
    need = [s for s in stations if s["status"] != "balanced"]
    return {"root": "desk", "elements": {
        "desk": {"type": "Card", "props": {"title": "Rebalancing desk"}, "children": ["kpis", "sim", "buttons"]},
        "kpis": {"type": "Row", "props": {}, "children": ["m1", "m2"]},
        "m1": {"type": "Metric", "props": {"label": "Bikes docked", "value": f"{sum(s['bikes'] for s in stations)} / {sum(s['capacity'] for s in stations)}"}},
        "m2": {"type": "Metric", "props": {"label": "Need attention", "value": len(need)}},
        "sim": {"type": "GeneratedView", "props": {"artifact": "sim", "height": 250}},
        "buttons": {"type": "Row", "props": {}, "children": ["refresh"]},
        "refresh": {"type": "Button", "props": {"label": "Refresh numbers", "action": "refresh", "variant": "secondary"}},
    }}


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if results:
        first = results[0]
        if first.get("is_error"):
            return [text("Nothing moved." if "denied" in first["content"] else f"That failed: {first['content']}")]
        try:
            data = json.loads(first["content"])
        except ValueError:
            return [text("Done.")]  # render results: nothing more to do
        stations = data["stations"]
        if "moved" in data:
            message = f"Moved {data['moved']} bikes from {data['from']} to {data['to']}."
            return [tool("render_ui", {"view": "desk", "spec": desk(stations)}),
                    tool("send_to_view", {"view": "sim", "data": {"stations": stations, "message": message}}), text(message)]
        rendered_before = any(b.get("name") == "render_ui" for m in messages if m["role"] == "assistant" for b in m["content"])
        if rendered_before:
            return [tool("render_ui", {"view": "desk", "spec": desk(stations)}),
                    tool("send_to_view", {"view": "sim", "data": {"stations": stations, "message": "Numbers refreshed."}})]
        names = ", ".join(s["name"] for s in stations if s["status"] != "balanced")
        return [tool("show_alert", {"level": "warning", "text": f"Needs attention: {names}."}),
                tool("render_html", {"view": "sim", "title": "Rebalancing simulator", "html": bikes.REBALANCE_SIMULATOR_HTML,
                                     "actions": ["rebalance"], "placement": "embedded"}),
                tool("render_ui", {"view": "desk", "spec": desk(stations)}),
                tool("send_to_view", {"view": "sim", "data": {"stations": stations}})]
    prompt = last_user_text(messages)
    marker = prompt.rfind("[ui action] rebalance")
    if marker >= 0:
        plan = json.loads(prompt[marker:].split(" ", 3)[3].rsplit(" (from view", 1)[0])
        return [text("That plan moves bikes, so it needs your approval."),
                tool("rebalance", {"source": plan["from"], "target": plan["to"], "count": int(plan["count"])})]
    return [tool("query_stations", {})]


def make_harness(llm=None) -> Harness:
    return Harness(llm or get_llm(respond), SYSTEM, make_registry(bikes.Network()))
