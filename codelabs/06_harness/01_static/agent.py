"""Harness, static mode: render tools.

The harness gains three tools whose only job is to show something:
show_metric, show_table and show_chart. Each returns a short result for the
model ("displayed ...") and a ``ui`` event for the surfaces. The components
themselves are pre-built in each surface: rich renderables in the terminal,
DOM widgets in the browser. The model picks them and fills their props.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, text, tool, tool_results  # noqa: E402
from harness.loop import Harness  # noqa: E402
from harness.tools import Registry, obj  # noqa: E402

S, N = {"type": "string"}, {"type": ["number", "string"]}
ARRAY = {"type": "array"}
SYSTEM = ("You are an operations agent for a bike-share network. Read data with query_stations, "
          "then show results with show_metric, show_chart and show_table (the user sees them), "
          "then answer in two sentences.")


def make_registry(network: bikes.Network) -> Registry:
    registry = Registry()
    views = itertools.count(1)

    def ui(component, props):
        return {"type": "ui", "kind": "component", "view": f"v{next(views)}", "component": component, "props": props}

    @registry.add("query_stations", "Read live numbers for every station.", obj())
    def query_stations():
        return {"stations": [{"name": s["name"], "bikes": s["bikes"], "capacity": s["capacity"], "status": bikes.status(s)}
                             for s in network.stations]}

    @registry.add("show_metric", "Show the user one labelled number.", obj(["label", "value"], label=S, value=N, delta=S))
    def show_metric(label, value, delta=None):
        return f"displayed metric {label}", [ui("Metric", {"label": label, "value": value, "delta": delta})]

    @registry.add("show_table", "Show the user a table.", obj(["columns", "rows"], columns=ARRAY, rows=ARRAY))
    def show_table(columns, rows):
        return f"displayed a table with {len(rows)} rows", [ui("Table", {"columns": columns, "rows": rows})]

    @registry.add("show_chart", "Show the user a bar chart.", obj(["title", "labels", "values"], title=S, labels=ARRAY, values=ARRAY))
    def show_chart(title, labels, values):
        return f"displayed chart {title}", [ui("BarChart", {"title": title, "labels": labels, "values": values})]

    return registry


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if not results:
        return [text("Let me read the network first."), tool("query_stations", {})]
    try:
        data = json.loads(results[0]["content"])
    except ValueError:
        data = {}  # render tools answer in plain words: "displayed ..."
    if "stations" in data:
        s = data["stations"]
        bad = [x for x in s if x["status"] != "balanced"]
        return [tool("show_metric", {"label": "Stations needing rebalancing", "value": len(bad), "delta": f"of {len(s)}"}),
                tool("show_metric", {"label": "Bikes docked", "value": f"{sum(x['bikes'] for x in s)} / {sum(x['capacity'] for x in s)}"}),
                tool("show_chart", {"title": "Bikes per station", "labels": [x["name"] for x in s], "values": [x["bikes"] for x in s]}),
                tool("show_table", {"columns": ["Station", "Bikes", "Capacity", "Status"],
                                    "rows": [[x["name"], x["bikes"], x["capacity"], x["status"]] for x in bad]})]
    return [text("Three stations need attention: Market St & 4th and Mission & 16th are nearly empty, "
                 "Ferry Building is nearly full. Moving bikes from Ferry Building fixes most of it.")]


def make_harness(llm=None) -> Harness:
    return Harness(llm or get_llm(respond), SYSTEM, make_registry(bikes.Network()))
