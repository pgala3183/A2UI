"""A2UI, static mode: the developer wrote the UI; the model only picks it.

The A2UI components below are hand-written and fixed. The model gets one
tool, ``show_template``, and its whole job is to choose a template and a
station. It cannot add, remove or rearrange a component. The application
then fills the template's data model from its own data source.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text, text, tool  # noqa: E402


def metric(prefix: str, label: str, path: str) -> list[dict]:
    """Three components that show one number: a column, a caption and a value."""
    return [
        {"id": f"{prefix}_box", "component": "Column", "children": [f"{prefix}_label", f"{prefix}_value"], "weight": 1},
        {"id": f"{prefix}_label", "component": "Text", "text": label, "variant": "caption"},
        {"id": f"{prefix}_value", "component": "Text", "text": {"path": path}, "variant": "h1"},
    ]


# Template 1: one station. Every value is a binding into the data model.
STATION_STATUS = [
    {"id": "root", "component": "Card", "child": "body"},
    {"id": "body", "component": "Column", "children": ["title", "status", "numbers", "rule", "updated", "refresh"]},
    {"id": "title", "component": "Text", "text": {"path": "/station/name"}, "variant": "h2"},
    {"id": "status", "component": "Text", "text": {"path": "/station/status"}, "variant": "caption"},
    {"id": "numbers", "component": "Row", "children": ["bikes_box", "docks_box", "rides_box"]},
    *metric("bikes", "Bikes available", "/station/bikes"),
    *metric("docks", "Free docks", "/station/docks"),
    *metric("rides", "Rides today", "/station/rides"),
    {"id": "rule", "component": "Divider"},
    {"id": "updated", "component": "Text", "text": {"path": "/station/updated"}, "variant": "caption"},
    {"id": "refresh_label", "component": "Text", "text": "Refresh"},
    {"id": "refresh", "component": "Button", "child": "refresh_label", "variant": "primary",
     "action": {"event": {"name": "refresh", "context": {"stationId": {"path": "/station/id"}}}}},
]

# Template 2: the whole network. The number of rows is fixed when the template
# is written: a static UI cannot grow a sixth row for a sixth station.
NETWORK_OVERVIEW = [
    {"id": "root", "component": "Card", "child": "body"},
    {"id": "body", "component": "Column", "children": ["title", "totals", "rule", *[f"s{i}" for i in range(5)]]},
    {"id": "title", "component": "Text", "text": "# Network overview"},
    {"id": "totals", "component": "Row", "children": ["bikes_box", "cap_box", "rides_box"]},
    *metric("bikes", "Bikes docked", "/summary/bikes"),
    *metric("cap", "Total docks", "/summary/capacity"),
    *metric("rides", "Rides today", "/summary/rides_today"),
    {"id": "rule", "component": "Divider"},
    *[c for i in range(5) for c in [
        {"id": f"s{i}", "component": "Row", "children": [f"s{i}_name", f"s{i}_bikes", f"s{i}_status"]},
        {"id": f"s{i}_name", "component": "Text", "text": {"path": f"/stations/{i}/name"}, "weight": 2},
        {"id": f"s{i}_bikes", "component": "Text", "text": {"path": f"/stations/{i}/bikes"}},
        {"id": f"s{i}_status", "component": "Text", "text": {"path": f"/stations/{i}/status"}, "variant": "caption"},
    ]],
]

TEMPLATES = {"station_status": STATION_STATUS, "network_overview": NETWORK_OVERVIEW}

TOOLS = [{
    "name": "show_template",
    "description": "Show one of the app's pre-built screens. station_status needs station_id; network_overview does not.",
    "input_schema": {
        "type": "object",
        "properties": {
            "template": {"enum": list(TEMPLATES)},
            "station_id": {"enum": [s["id"] for s in bikes.STATIONS]},
        },
        "required": ["template"],
        "additionalProperties": False,
    },
}]

SYSTEM = (
    "You are the assistant inside a bike-share operations app. Answer with one short sentence, "
    "then call show_template exactly once. Station ids: "
    + ", ".join(f"{s['id']} ({s['name']})" for s in bikes.STATIONS)
    + ". Use network_overview for questions about the whole network."
)


def respond(system: str, messages: list[dict]):
    """The scripted model: what a model is expected to do with this prompt."""
    prompt = last_user_text(messages).lower()
    if "network" in prompt or "all stations" in prompt:
        return [text("Here is the whole network."), tool("show_template", {"template": "network_overview"})]
    station = next((s for s in bikes.STATIONS if s["id"] in prompt or s["name"].lower() in prompt), bikes.STATIONS[0])
    return [text(f"Here is the live status of {station['name']}."),
            tool("show_template", {"template": "station_status", "station_id": station["id"]})]


def make_llm():
    return get_llm(respond)
