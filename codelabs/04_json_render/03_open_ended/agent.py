"""json-render, open-ended mode: a catalog with one HtmlArtifact element.

The model still speaks json-render (patches into an element map), but the
only component is an HTML document. JSON Patch cannot append to a string, so
the document streams as an array of chunks: each chunk is
{"op":"add","path":"/elements/calc/props/chunks/-","value":"..."}. The page
shows progress while chunks arrive and mounts the document when the model
sets props.complete to true. The server checks the whole document before it
lets that last patch through.
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
from jr import HTML_ARTIFACT, Catalog  # noqa: E402

CATALOG = Catalog({"HtmlArtifact": HTML_ARTIFACT},
                  actions={"book_ride": {"description": "Sent by the document: book a ride.",
                                         "params": {"minutes": {}, "ebike": {}, "member": {}, "cost": {}}}})


def html_policy(element_id: str, element: dict) -> list[str]:
    """Runs on every patch; the full document is checked once it claims to be complete."""
    props = element.get("props", {})
    if not props.get("complete"):
        return []
    return [f"/elements/{element_id}: {p}" for p in check_html("".join(props.get("chunks", [])))]


SYSTEM = f"""Reply with json-render JSON Patch operations, one per line, nothing else.
Create one HtmlArtifact with id "calc" and an empty chunks array, append the HTML document in
pieces of about 200 characters, then set props.complete to true. Put prices in /state/pricing.
The document reads state with genui.onData(state => ...) (state.pricing, state.message) and
sends genui.send("book_ride", {{minutes, ebike, member, cost}}).

{CATALOG.prompt()}"""


def respond(system: str, messages: list[dict]) -> str:
    html = bikes.TRIP_CALCULATOR_HTML
    ops = [{"op": "add", "path": "/root", "value": "calc"},
           {"op": "add", "path": "/elements/calc", "value": {"type": "HtmlArtifact", "props": {
               "title": "Trip cost calculator", "chunks": [], "complete": False, "height": 300}}},
           *[{"op": "add", "path": "/elements/calc/props/chunks/-", "value": html[i:i + 200]} for i in range(0, len(html), 200)],
           {"op": "replace", "path": "/elements/calc/props/complete", "value": True},
           {"op": "add", "path": "/state/pricing", "value": bikes.PRICING}]
    return "\n".join(json.dumps(op) for op in ops)


def make_llm():
    return get_llm(respond)
