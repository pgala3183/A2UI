"""A2UI, mixed mode: Basic Catalog components plus one HtmlFrame.

The dashboard's title, numbers and button are catalog components: cheap,
consistent, accessible, validated. Only the rebalancing simulator, which the
catalog cannot express, is model-written HTML. Both halves read the same
data model, so one updateDataModel from the server refreshes both.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import a2ui  # noqa: E402
from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm  # noqa: E402
from htmlframe import MIXED_CATALOG  # noqa: E402

SURFACE = "ops_dashboard"

SYSTEM = f"""You build user interfaces with A2UI {a2ui.VERSION}.
Reply with A2UI messages only, one JSON object per line. Use surfaceId "{SURFACE}"
and catalogId "{MIXED_CATALOG.id}".
Rule: build everything you can from catalog components (Text, Row, Column, Card,
Button...). Use HtmlFrame only for a part the catalog cannot express, such as an
interactive simulation, and use at most one. Bind values to the data model:
/summary (bikes, capacity, rides_today, attention), /stations (list), /message.
Allowed actions: refresh (Button), rebalance (from the HtmlFrame: from, to, count).

{MIXED_CATALOG.prompt()}"""


def metric(prefix: str, label: str, path: str) -> list[dict]:
    return [
        {"id": f"{prefix}_box", "component": "Column", "children": [f"{prefix}_label", f"{prefix}_value"], "weight": 1},
        {"id": f"{prefix}_label", "component": "Text", "text": label, "variant": "caption"},
        {"id": f"{prefix}_value", "component": "Text", "text": {"path": path}, "variant": "h1"},
    ]


def respond(system: str, messages: list[dict]) -> str:
    def m(kind, body):
        return json.dumps({"version": a2ui.VERSION, kind: {"surfaceId": SURFACE, **body}})

    return "\n".join([
        m("createSurface", {"catalogId": MIXED_CATALOG.id}),
        m("updateComponents", {"components": [
            {"id": "root", "component": "Card", "child": "body"},
            {"id": "body", "component": "Column", "children": ["title", "totals", "attention", "rule", "sim", "message", "buttons"]},
            {"id": "title", "component": "Text", "text": "# Rebalancing desk"},
            {"id": "totals", "component": "Row", "children": ["bikes_box", "cap_box", "rides_box"]},
            *metric("bikes", "Bikes docked", "/summary/bikes"),
            *metric("cap", "Total docks", "/summary/capacity"),
            *metric("rides", "Rides today", "/summary/rides_today"),
            {"id": "attention", "component": "Text", "text": {"path": "/summary/attention"}, "variant": "caption"},
            {"id": "rule", "component": "Divider"},
        ]}),
        # The one part the catalog cannot express: an interactive what-if simulator.
        m("updateComponents", {"components": [
            {"id": "sim", "component": "HtmlFrame", "title": "Rebalancing simulator", "height": 250,
             "html": bikes.REBALANCE_SIMULATOR_HTML},
        ]}),
        m("updateComponents", {"components": [
            {"id": "message", "component": "Text", "text": {"path": "/message"}},
            {"id": "buttons", "component": "Row", "children": ["refresh"]},
            {"id": "refresh_label", "component": "Text", "text": "Refresh numbers"},
            {"id": "refresh", "component": "Button", "child": "refresh_label", "variant": "borderless",
             "action": {"event": {"name": "refresh"}}},
        ]}),
    ])


def make_llm():
    return get_llm(respond)
