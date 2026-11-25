"""OpenUI Lang, open-ended mode: HtmlArtifact(title, document, data).

    python server.py            then open http://127.0.0.1:8503

The library has one component. The model writes ``root`` first, then the
small ``prices`` statement, then the long ``doc`` string on one line. While
that line streams the page shows progress ("generating... N characters");
the server checks the document with the content policy before accepting
the line. A booking from inside the sandbox comes back as a new ``prices``
statement, which replaces the old one, and the frame receives it as data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import openui  # noqa: E402
from openui import p  # noqa: E402
from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

LIBRARY = {"HtmlArtifact": {
    "description": "An interactive HTML document in a sandboxed iframe (inline CSS/JS, no network). "
                   "data is pushed into it: genui.onData(fn). It sends actions with genui.send(name, payload).",
    "params": [p("title", "string"), p("document", "string"), p("data", "object", optional=True)]}}
SYSTEM = (openui.prompt(LIBRARY) + "\nOne statement per line; put the document in its own statement "
          "(a JSON string on one line), after the short ones. For a trip calculator the document sends "
          'genui.send("book_ride", {minutes, ebike, member, cost}) and reads data.pricing and data.message.')


def respond(system: str, messages: list[dict]) -> str:
    return "\n".join([
        'root = HtmlArtifact("Trip cost calculator", doc, prices)',
        f"prices = {json.dumps({'pricing': bikes.PRICING})}",
        f"doc = {json.dumps(bikes.TRIP_CALCULATOR_HTML)}",
    ])


llm = get_llm(respond)
network = bikes.Network()
app = openui.make_app(HERE, LIBRARY, "OpenUI open-ended")
session = {"gate": openui.StatementGate(LIBRARY, extra_check=openui.artifact_policy)}


@app.post("/run")
def run(request):
    session["gate"] = openui.StatementGate(LIBRARY, extra_check=openui.artifact_policy)
    yield from openui.generate(llm, SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}], session["gate"])


@app.post("/action")
def action(request):
    body = request.json
    params = body.get("params") or {}
    if body.get("action") != "book_ride" or body.get("source") != "root":
        yield ("error", {"message": "only the artifact may send book_ride"})
        return
    minutes = params.get("minutes")
    if isinstance(minutes, (int, float)) and 5 <= minutes <= 180:
        price = network.ride_cost(minutes, bool(params.get("ebike")), bool(params.get("member")))
        message = f"Booked: {int(minutes)} min for ${price:.2f} (server price)."
    else:
        message = "Not booked: minutes must be 5 to 180."
    line = f"prices = {json.dumps({'pricing': network.pricing, 'message': message})}"  # replaces the old statement
    errors = session["gate"].offer(line)
    yield ("refused", {"errors": errors}) if errors else ("line", {"line": line})


if __name__ == "__main__":
    app.run(port_from_argv(8503))
