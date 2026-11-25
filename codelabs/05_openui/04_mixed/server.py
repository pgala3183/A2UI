"""OpenUI Lang, mixed mode: catalog statements plus one HtmlArtifact.

    python server.py            then open http://127.0.0.1:8504

The prompt carries OpenUI's own rule for the html-artifact pattern: use the
artifact only for something interactive the library cannot express. The
application answers actions in OpenUI Lang too: it resends the few
statements that changed (two metrics, a note, the simulator's data), and
each replaces the old statement with the same id. The artifact's document
does not change, so the live iframe stays where it is.
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

LIBRARY = {
    "Stack": {"description": "Children in a row or a column.",
              "params": [p("children", "list"), p("direction", "string", optional=True, enum=["row", "column"])]},
    "Card": {"description": "A titled section.", "params": [p("title", "string"), p("children", "list")]},
    "Text": {"description": "Text.", "params": [p("text", "text"), p("variant", "string", optional=True, enum=["h2", "body", "caption"])]},
    "Markdown": {"description": "A short paragraph with **bold** and `code`.", "params": [p("text", "string")]},
    "Metric": {"description": "A labelled number.", "params": [p("label", "string"), p("value", "text")]},
    "Button": {"description": "Sends an action.", "params": [p("label", "string"), p("action", "string", enum=["refresh"]),
                                                              p("variant", "string", optional=True, enum=["primary", "secondary"])]},
    "HtmlArtifact": {"description": "Interactive HTML in a sandbox; only for what the other components cannot express.",
                     "params": [p("title", "string"), p("document", "string"), p("data", "object", optional=True)]},
}
SYSTEM = (openui.prompt(LIBRARY) + "\nUse the library components for everything you can. Use one HtmlArtifact only when "
          "the user needs something interactive the library cannot express (a simulator); inline CSS/JS only. "
          "The simulator reads data.stations and sends genui.send(\"rebalance\", {from, to, count}).")
network = bikes.Network()


def data_lines(message: str) -> list[str]:
    """The statements the application owns: numbers, the note, the simulator's data."""
    summary = network.summary()
    names = ", ".join(network.get(i)["name"] for i in summary["needs_attention"]) or "none"
    stations = [{k: s[k] for k in ("id", "name", "bikes", "capacity")} for s in network.stations]
    return [f'bikes = Metric("Bikes docked", "{summary["bikes"]} / {summary["capacity"]}")',
            f'need = Metric("Need attention", {len(summary["needs_attention"])})',
            f"attention = Text({json.dumps('Needs attention: ' + names)}, \"caption\")",
            f"note = Markdown({json.dumps(message)})",
            f"simData = {json.dumps({'stations': stations, 'message': message})}"]


def respond(system: str, messages: list[dict]) -> str:
    return "\n".join([
        "root = Stack([header, sim, note, actions])",
        'header = Card("Rebalancing desk", [kpis, attention])',
        'kpis = Stack([bikes, need], "row")',
        'sim = HtmlArtifact("Rebalancing simulator", simDoc, simData)',
        'actions = Stack([refresh], "row")',
        'refresh = Button("Refresh numbers", "refresh", "secondary")',
        *data_lines("Pick two stations in the simulator and **apply a plan**."),
        f"simDoc = {json.dumps(bikes.REBALANCE_SIMULATOR_HTML)}",
    ])


llm = get_llm(respond)
app = openui.make_app(HERE, LIBRARY, "OpenUI mixed")
session = {"gate": openui.StatementGate(LIBRARY, extra_check=openui.artifact_policy)}


@app.post("/run")
def run(request):
    global network
    network = bikes.Network()
    session["gate"] = openui.StatementGate(LIBRARY, extra_check=openui.artifact_policy)
    yield from openui.generate(llm, SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}], session["gate"])


@app.post("/action")
def action(request):
    body = request.json
    params = body.get("params") or {}
    if body.get("action") == "rebalance" and body.get("source") == "sim":
        ids = {s["id"] for s in network.stations}
        if params.get("from") in ids and params.get("to") in ids and params["from"] != params["to"]:
            result = network.rebalance(params["from"], params["to"], params.get("count", 0))
        else:
            result = {"ok": False, "error": "pick two different stations"}
        message = (f"Moved **{result['moved']}** bikes from {result['from']} to {result['to']}." if result["ok"]
                   else f"Not applied: {result['error']}.")
    elif body.get("action") == "refresh" and body.get("source") == "button":
        message = "Numbers refreshed."
    else:
        yield ("error", {"message": f"{body.get('action')!r} from {body.get('source')!r} is not allowed"})
        return
    for line in data_lines(message):
        errors = session["gate"].offer(line)
        yield ("refused", {"errors": errors}) if errors else ("line", {"line": line})


if __name__ == "__main__":
    app.run(port_from_argv(8504))
