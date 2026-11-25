"""Harness, declarative mode: one render_ui tool that takes a whole spec.

Instead of one tool per component, the model composes a layout from a
catalog and passes it to ``render_ui``. The tool validates the spec. An
invalid spec is not an exception: it is an error *result*, and the loop
hands it back to the model, which fixes the spec on its next turn. The
scripted model makes two typical mistakes the first time.
"""

from __future__ import annotations


import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.elements import CATALOG_V1  # noqa: E402
from genui_common.llm import get_llm, text, tool, tool_results  # noqa: E402
from harness.loop import Harness  # noqa: E402
from harness.tools import Registry, ToolError, obj  # noqa: E402

SPEC = {"type": "object", "properties": {"root": {"type": "string"}, "elements": {"type": "object"}},
        "required": ["root", "elements"]}
SYSTEM = ("You are an operations agent for a bike-share network. Read data with query_stations. Show results "
          "with render_ui(view, spec): spec = {root, elements: {id: {type, props, children}}}. If render_ui "
          "returns an error, fix the spec and call it again.\n" + CATALOG_V1.prompt())


def make_registry(network: bikes.Network) -> Registry:
    registry = Registry()

    @registry.add("query_stations", "Read live numbers for every station.", obj())
    def query_stations():
        return {"stations": [{"name": s["name"], "bikes": s["bikes"], "capacity": s["capacity"], "status": bikes.status(s)}
                             for s in network.stations], "rides_today": network.summary()["rides_today"]}

    @registry.add("render_ui", "Render a declarative UI spec for the user.", obj(["view", "spec"], view={"type": "string"}, spec=SPEC))
    def render_ui(view, spec):
        errors = CATALOG_V1.check_spec(spec)
        if errors:
            raise ToolError("invalid spec: " + "; ".join(errors[:6]))
        actions = sorted({e["props"]["action"] for e in spec["elements"].values() if e["type"] == "Button"})
        event = {"type": "ui", "kind": "spec", "view": view, "spec": spec, "actions": actions}
        return f"rendered view {view} with {len(spec['elements'])} elements", [event]

    return registry


def dashboard(data: dict, broken: bool) -> dict:
    s = data["stations"]
    bad = [x for x in s if x["status"] != "balanced"]
    elements = {
        "dash": {"type": "Card", "props": {"title": "Rebalancing report"}, "children": ["kpis", "chart", "table"]},
        "kpis": {"type": "Row", "props": {}, "children": ["m1", "m2"]},
        "m1": {"type": "Metric", "props": {"label": "Need attention", "value": len(bad), "delta": f"of {len(s)}"}},
        "m2": {"type": "Metric", "props": {"label": "Rides today", "value": data["rides_today"]}},
        "chart": {"type": "BarChart", "props": {"title": "Bikes per station", "labels": [x["name"] for x in s],
                                                "values": [x["bikes"] for x in s]}},
        "table": {"type": "Table", "props": {"columns": ["Station", "Bikes", "Status"],
                                             "rows": [[x["name"], x["bikes"], x["status"]] for x in bad]}},
    }
    if broken:  # two classic first-attempt mistakes: an invented type and a dangling child
        elements["chart"]["type"] = "PieChart"
        elements["dash"]["children"].append("footer")
    return {"root": "dash", "elements": elements}


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if not results:
        return [text("Reading the network."), tool("query_stations", {})]
    content = results[0]["content"]
    if '"stations"' in content:
        return [tool("render_ui", {"view": "report", "spec": dashboard(json.loads(content), broken=True)})]
    if results[0].get("is_error"):
        # the next attempt: the spec built from the same data, without the mistakes
        data = next(json.loads(b["content"]) for m in messages if m["role"] == "user" and isinstance(m["content"], list)
                    for b in m["content"] if b.get("type") == "tool_result" and '"stations"' in b["content"])
        return [text("I used a type that is not in the catalog; fixing it."),
                tool("render_ui", {"view": "report", "spec": dashboard(data, broken=False)})]
    return [text("The report is on screen: three stations need attention.")]


def make_harness(llm=None) -> Harness:
    return Harness(llm or get_llm(respond), SYSTEM, make_registry(bikes.Network()))


