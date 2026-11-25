"""json-render, mixed mode: primitives + one HtmlArtifact + actions of both kinds.

* catalog primitives for the numbers, text, table and button;
* one HtmlArtifact for the simulator the primitives cannot express;
* setState (built in) toggles the table in the browser, no round trip;
* rebalance (custom) goes to the server and comes back as /state patches,
  which update the catalog elements and the artifact alike.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm  # noqa: E402
from genui_common.sandbox import check_html  # noqa: E402
from jr import HTML_ARTIFACT, PRIMITIVES, Catalog  # noqa: E402

CATALOG = Catalog({**PRIMITIVES, "HtmlArtifact": HTML_ARTIFACT}, actions={
    "rebalance": {"description": "Sent by the simulator: move bikes.", "params": {"from": {}, "to": {}, "count": {}}}})


def html_policy(element_id: str, element: dict) -> list[str]:
    props = element.get("props", {})
    if element.get("type") != "HtmlArtifact" or not props.get("complete"):
        return []
    return [f"/elements/{element_id}: {p}" for p in check_html("".join(props.get("chunks", [])))]


SYSTEM = f"""Reply with json-render JSON Patch operations, one per line, nothing else.
Use catalog primitives for everything you can; add at most one HtmlArtifact, only for an
interactive part the primitives cannot express. Bind data with {{"$state": "/path"}}. State:
/summary (bikes, attention, names), /stations, /rows, /message, /ui/showTable.
Use the built-in setState for view-only toggles; use rebalance only from the artifact.

{CATALOG.prompt()}"""


def state(network: bikes.Network, message: str) -> dict:
    summary = network.summary()
    names = ", ".join(network.get(i)["name"] for i in summary["needs_attention"]) or "none"
    return {"summary": {"bikes": f"{summary['bikes']} / {summary['capacity']}", "attention": len(summary["needs_attention"]),
                        "names": f"Needs attention: {names}"},
            "stations": [{k: s[k] for k in ("id", "name", "bikes", "capacity")} for s in network.stations],
            "rows": network.table(), "message": message}


def respond(system: str, messages: list[dict]) -> str:
    def el(eid, kind, props, children=None, **extra):
        return {"op": "add", "path": f"/elements/{eid}",
                "value": {"type": kind, "props": props, **({"children": children} if children else {}), **extra}}

    html = bikes.REBALANCE_SIMULATOR_HTML
    ops = [
        {"op": "add", "path": "/root", "value": "desk"},
        el("desk", "Card", {"title": "Rebalancing desk"}, ["kpis", "names", "sim", "toggle", "table"]),
        el("kpis", "Row", {}, ["m1", "m2"]),
        el("m1", "Metric", {"label": "Bikes docked", "value": {"$state": "/summary/bikes"}}),
        el("m2", "Metric", {"label": "Need attention", "value": {"$state": "/summary/attention"}}),
        el("names", "Text", {"text": {"$state": "/summary/names"}, "variant": "caption"}),
        el("sim", "HtmlArtifact", {"title": "Rebalancing simulator", "chunks": [], "height": 250}),
        *[{"op": "add", "path": "/elements/sim/props/chunks/-", "value": html[i:i + 400]} for i in range(0, len(html), 400)],
        {"op": "add", "path": "/elements/sim/props/complete", "value": True},
        el("toggle", "Button", {"label": "Show / hide station table", "variant": "secondary"},
           on={"press": {"action": "setState", "params": {"statePath": "/ui/showTable",
                                                           "value": {"$not": {"$state": "/ui/showTable"}}}}}),
        el("table", "Table", {"columns": ["Station", "Bikes", "Free docks", "Status"], "rows": {"$state": "/rows"}},
           visible={"$state": "/ui/showTable"}),
        *[{"op": "add", "path": f"/state/{k}", "value": v}
          for k, v in state(bikes.Network(), "Pick two stations and apply a plan.").items()],
        {"op": "add", "path": "/state/ui", "value": {"showTable": False}},
    ]
    return "\n".join(json.dumps(op) for op in ops)


def make_llm():
    return get_llm(respond)
