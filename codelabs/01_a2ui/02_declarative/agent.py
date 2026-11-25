"""A2UI, declarative mode: the model writes the components itself.

The system prompt carries the catalog (component names and props). The model
answers with A2UI messages, one JSON object per line. Nothing forces the
output to be valid, so the server validates every line against the catalog
and returns the errors to the model as the next user turn: a correction loop.
The scripted model makes one realistic mistake on its first attempt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import a2ui  # noqa: E402
from genui_common.llm import get_llm, last_user_text  # noqa: E402

SURFACE = "report_form"
ACTIONS = {"submit_report": "context: station, bike, issue, urgent (bind each to the data model)"}

SYSTEM = f"""You build user interfaces with A2UI {a2ui.VERSION}.
Reply with A2UI messages only, one JSON object per line, no prose, no code fences.
Order: createSurface, then updateComponents (you may send several, a section at a
time, so the page can paint early), then updateDataModel with initial values.
Every message has "version": "{a2ui.VERSION}". Components form a flat list joined by
ids; exactly one component has id "root". Bind inputs to the data model with
{{"path": "/json/pointer"}}. Buttons send actions to the server; allowed actions:
{json.dumps(ACTIONS)}.
Use surfaceId "{SURFACE}" and catalogId "{a2ui.BASIC_CATALOG_ID}".

{a2ui.BASIC_CATALOG.prompt()}"""


def m(kind: str, body: dict) -> str:
    return json.dumps({"version": a2ui.VERSION, kind: {"surfaceId": SURFACE, **body}}, separators=(",", ":"))


def reply(first_attempt: bool) -> str:
    """The lines a model writes for 'report a broken bike'."""
    issue = ({"id": "issue_field", "component": "Dropdown", "label": "What is wrong?",  # not in the catalog
              "options": ["flat tyre", "brakes", "chain"], "value": {"path": "/report/issue"}}
             if first_attempt else
             {"id": "issue_field", "component": "TextField", "label": "What is wrong?",
              "value": {"path": "/report/issue"}, "variant": "longText"})
    return "\n".join([
        m("createSurface", {"catalogId": a2ui.BASIC_CATALOG_ID}),
        # section 1: the frame. Its children do not exist yet; the page shows skeletons.
        m("updateComponents", {"components": [
            {"id": "root", "component": "Card", "child": "body"},
            {"id": "body", "component": "Column", "children": ["title", "intro", "fields", "send_row", "result"]},
            {"id": "title", "component": "Text", "text": "# Report a broken bike"},
            {"id": "intro", "component": "Text", "text": "Tell the repair crew what you found.", "variant": "caption"},
        ]}),
        # section 2: the inputs, each bound two-way to /report/...
        m("updateComponents", {"components": [
            {"id": "fields", "component": "Column", "children": ["where_row", "issue_field", "urgent_box"]},
            {"id": "where_row", "component": "Row", "children": ["station_field", "bike_field"]},
            {"id": "station_field", "component": "TextField", "label": "Station", "value": {"path": "/report/station"}},
            {"id": "bike_field", "component": "TextField", "label": "Bike number", "value": {"path": "/report/bike"}},
            issue,
            {"id": "urgent_box", "component": "CheckBox", "label": "Unsafe to ride", "value": {"path": "/report/urgent"}},
        ]}),
        # section 3: the action and a place for the server's answer
        m("updateComponents", {"components": [
            {"id": "send_row", "component": "Row", "children": ["send"]},
            {"id": "send_label", "component": "Text", "text": "Send report"},
            {"id": "send", "component": "Button", "child": "send_label", "variant": "primary",
             "action": {"event": {"name": "submit_report", "context": {
                 "station": {"path": "/report/station"}, "bike": {"path": "/report/bike"},
                 "issue": {"path": "/report/issue"}, "urgent": {"path": "/report/urgent"}}}}},
            {"id": "result", "component": "Text", "text": {"path": "/report/result"}, "variant": "caption"},
        ]}),
        m("updateDataModel", {"path": "/report", "value": {
            "station": "Market St & 4th", "bike": "", "issue": "", "urgent": False, "result": ""}}),
    ])


def respond(system: str, messages: list[dict]) -> str:
    return reply(first_attempt="failed validation" not in last_user_text(messages))


def make_llm():
    return get_llm(respond)
