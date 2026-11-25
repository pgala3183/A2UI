"""AG-UI, declarative mode: the UI is shared state.

AG-UI has first-class shared state: STATE_SNAPSHOT sends all of it,
STATE_DELTA sends RFC 6902 JSON Patch operations. Here the state holds a
declarative UI (a flat element map from a catalog). The model writes one
element per line; the server turns each line into a STATE_DELTA, so the
dashboard grows on screen while the model is still writing. On the next run
the page sends the state back, and the model rewrites only what changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.elements import CATALOG_V1  # noqa: E402
from genui_common.llm import get_llm, last_user_text  # noqa: E402

CATALOG = CATALOG_V1
NETWORK = bikes.Network()


def system_for(state: dict) -> str:
    current = sorted(state.get("ui", {}).get("elements", {}))
    return f"""You maintain the user interface of a bike-share dashboard. The UI lives in shared
state as a flat element map. Reply with one element per line and nothing else:
{{"id": "...", "type": "...", "props": {{...}}, "children": ["child ids"]}}
The root element has id "dash". To change an existing UI, write only the elements
that change, with the same id. Buttons send "[ui action] <action> <params>" to you.
Network data (station, bikes, free docks, status): {json.dumps(NETWORK.table())}
Elements currently in state: {current or "none"}

{CATALOG.prompt()}"""


def elements(view: str = "all") -> list[dict]:
    rows = NETWORK.table()
    if view == "attention":
        rows = [r for r in rows if r[3] != "balanced"]
    summary = NETWORK.summary()
    title = "Stations needing attention" if view == "attention" else "Network dashboard"
    return [
        {"id": "dash", "type": "Card", "props": {"title": title, "subtitle": f"{len(rows)} stations"},
         "children": ["kpis", "chart", "table", "actions"]},
        {"id": "kpis", "type": "Row", "props": {}, "children": ["m_bikes", "m_rides", "m_attention"]},
        {"id": "m_bikes", "type": "Metric", "props": {"label": "Bikes docked", "value": f"{summary['bikes']} / {summary['capacity']}"}},
        {"id": "m_rides", "type": "Metric", "props": {"label": "Rides today", "value": summary["rides_today"], "delta": "+6%"}},
        {"id": "m_attention", "type": "Metric", "props": {"label": "Need attention", "value": len(summary["needs_attention"])}},
        {"id": "chart", "type": "BarChart", "props": {"title": "Bikes per station", "labels": [r[0] for r in rows],
                                                        "values": [r[1] for r in rows]}},
        {"id": "table", "type": "Table", "props": {"columns": ["Station", "Bikes", "Free docks", "Status"], "rows": rows}},
        {"id": "actions", "type": "Row", "props": {}, "children": ["only_attention", "show_all"]},
        {"id": "only_attention", "type": "Button", "props": {"label": "Only stations needing attention", "action": "filter_attention"}},
        {"id": "show_all", "type": "Button", "props": {"label": "Show all", "action": "show_all", "variant": "secondary"}},
    ]


def respond(system: str, messages: list[dict]) -> str:
    prompt = last_user_text(messages)
    if "[ui action] filter_attention" in prompt:
        changed = [e for e in elements("attention") if e["id"] in ("dash", "chart", "table")]
    elif "[ui action] show_all" in prompt:
        changed = [e for e in elements("all") if e["id"] in ("dash", "chart", "table")]
    else:
        changed = elements("all")
    return "\n".join(json.dumps(e) for e in changed)


def make_llm():
    return get_llm(respond)
