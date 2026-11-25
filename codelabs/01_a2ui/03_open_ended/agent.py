"""A2UI, open-ended mode: a catalog with one component that holds HTML.

The model is no longer limited to catalog layouts. It writes a complete HTML
document for a trip-cost calculator and wraps it in one ``HtmlFrame``. A2UI
still carries it: the surface, the data model and the action envelope are
unchanged. Only the catalog is different.
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
from htmlframe import OPEN_CATALOG  # noqa: E402

SURFACE = "trip_calculator"

SYSTEM = f"""You build user interfaces with A2UI {a2ui.VERSION} and a custom catalog.
Reply with A2UI messages only, one JSON object per line: createSurface, updateComponents,
updateDataModel. Use surfaceId "{SURFACE}" and catalogId "{OPEN_CATALOG.id}".
The whole interface is one HtmlFrame component with id "root". Write a complete HTML
document: inline CSS and JS only, no external URLs, no network calls, no storage.
Read prices from the data model with genui.onData(data => ...) (data.pricing has
unlock, per_minute, ebike_per_minute, member_discount) and show data.message if present.
When the user books, call genui.send("book_ride", {{minutes, ebike, member, cost}}).

{OPEN_CATALOG.prompt()}"""


def respond(system: str, messages: list[dict]) -> str:
    """What a model writes: three messages, the middle one carrying the whole document."""
    def m(kind, body):
        return json.dumps({"version": a2ui.VERSION, kind: {"surfaceId": SURFACE, **body}})

    return "\n".join([
        m("createSurface", {"catalogId": OPEN_CATALOG.id}),
        m("updateComponents", {"components": [{"id": "root", "component": "HtmlFrame", "title": "Trip cost calculator",
                                               "height": 300, "html": bikes.TRIP_CALCULATOR_HTML}]}),
        m("updateDataModel", {"path": "/pricing", "value": bikes.PRICING}),
    ])


def make_llm():
    return get_llm(respond)
