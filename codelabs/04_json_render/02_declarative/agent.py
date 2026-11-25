"""json-render, declarative mode: primitives, state bindings, streamed patches.

The catalog now holds layout primitives (Card, Row, Metric, Table, ...).
The model composes them and streams the spec as JSON Patch lines, so the
page paints the frame first and fills it in. Values bind to ``/state`` with
{"$state": "/path"}: a later patch to state updates every bound element.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm  # noqa: E402
from jr import PRIMITIVES, Catalog  # noqa: E402

CATALOG = Catalog(PRIMITIVES, actions={"refresh": {"description": "Reload the numbers.", "params": {}}})

SYSTEM = f"""You build dashboards as json-render specs, streamed as RFC 6902 JSON Patch.
Write one operation per line, nothing else. Start with {{"op":"add","path":"/root","value":"<id>"}},
then add elements top-down ("/elements/<id>"), then the data under "/state/...".
Bind numbers to state with {{"$state": "/path"}} instead of copying them into props.

{CATALOG.prompt()}"""


def state(network: bikes.Network) -> dict:
    summary = network.summary()
    return {"summary": {"bikes": f"{summary['bikes']} / {summary['capacity']}", "rides": summary["rides_today"],
                        "attention": len(summary["needs_attention"])},
            "chart": {"labels": [s["name"] for s in network.stations], "values": [s["bikes"] for s in network.stations]},
            "rows": network.table()}


def ops(network: bikes.Network) -> list[dict]:
    def el(eid, kind, props, children=None, on=None):
        value = {"type": kind, "props": props, **({"children": children} if children else {}), **({"on": on} if on else {})}
        return {"op": "add", "path": f"/elements/{eid}", "value": value}

    data = state(network)
    return [
        {"op": "add", "path": "/root", "value": "dash"},
        el("dash", "Card", {"title": "Network dashboard", "subtitle": "live"}, ["kpis", "chart", "table", "refresh"]),
        el("kpis", "Row", {}, ["m1", "m2", "m3"]),
        el("m1", "Metric", {"label": "Bikes docked", "value": {"$state": "/summary/bikes"}}),
        el("m2", "Metric", {"label": "Rides today", "value": {"$state": "/summary/rides"}}),
        el("m3", "Metric", {"label": "Need attention", "value": {"$state": "/summary/attention"}}),
        el("chart", "BarChart", {"title": "Bikes per station", "labels": {"$state": "/chart/labels"},
                                 "values": {"$state": "/chart/values"}}),
        el("table", "Table", {"columns": ["Station", "Bikes", "Free docks", "Status"], "rows": {"$state": "/rows"}}),
        el("refresh", "Button", {"label": "Refresh", "variant": "secondary"}, on={"press": {"action": "refresh", "params": {}}}),
        *[{"op": "add", "path": f"/state/{key}", "value": value} for key, value in data.items()],
    ]


def respond(system: str, messages: list[dict]) -> str:
    return "\n".join(json.dumps(op) for op in ops(bikes.Network()))


def make_llm():
    return get_llm(respond)
