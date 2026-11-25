"""OpenUI Lang, declarative mode: layouts, forward references, partial updates.

    python server.py            then open http://127.0.0.1:8502

The model writes ``root`` first and names children that do not exist yet.
The page paints that frame at once (skeletons for the missing ids) and fills
it in line by line. A button action asks the model again; it answers with
only the statements that change, and each replaces the old one by id.
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
from genui_common.llm import get_llm, last_user_text  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

LIBRARY = {
    "Card": {"description": "A titled section.", "params": [p("title", "string"), p("children", "list")]},
    "Stack": {"description": "Children in a row or a column.",
              "params": [p("children", "list"), p("direction", "string", optional=True, enum=["row", "column"]),
                         p("gap", "string", optional=True, enum=["s", "m", "l"])]},
    "Text": {"description": "Text.", "params": [p("text", "text"), p("variant", "string", optional=True, enum=["h2", "h3", "body", "caption"])]},
    "Metric": {"description": "A labelled number.", "params": [p("label", "string"), p("value", "text"), p("delta", "string", optional=True)]},
    "BarChart": {"description": "A bar chart.", "params": [p("title", "string"), p("labels", "list"), p("values", "list")]},
    "Table": {"description": "A table.", "params": [p("columns", "list"), p("rows", "list")]},
    "Button": {"description": "Sends an action to the server.",
               "params": [p("label", "string"), p("action", "string", enum=["filter_attention", "show_all"]),
                          p("variant", "string", optional=True, enum=["primary", "secondary"])]},
}
NETWORK = bikes.Network()
SYSTEM = (openui.prompt(LIBRARY) + "\nWrite root first, then define each name it uses, top-down. "
          "To change a UI later, send only the statements that change. Data: " + json.dumps(NETWORK.table()))


def program(view: str) -> dict[str, str]:
    rows = NETWORK.table() if view == "all" else [r for r in NETWORK.table() if r[3] != "balanced"]
    summary = NETWORK.summary()
    title = "Network dashboard" if view == "all" else "Stations needing attention"
    return {
        "root": f'root = Card("{title}", [kpis, chart, table, actions])',
        "kpis": "kpis = Stack([bikes, rides, attention], \"row\")",
        "bikes": f'bikes = Metric("Bikes docked", "{summary["bikes"]} / {summary["capacity"]}")',
        "rides": f'rides = Metric("Rides today", {summary["rides_today"]}, "+6%")',
        "attention": f'attention = Metric("Need attention", {len(summary["needs_attention"])})',
        "chart": "chart = BarChart(\"Bikes per station\", names, counts)",
        "names": f"names = {json.dumps([r[0] for r in rows])}",
        "counts": f"counts = {json.dumps([r[1] for r in rows])}",
        "table": "table = Table([\"Station\", \"Bikes\", \"Free docks\", \"Status\"], rows)",
        "rows": f"rows = {json.dumps(rows)}",
        "actions": "actions = Stack([onlyAttention, showAll], \"row\")",
        "onlyAttention": 'onlyAttention = Button("Only stations needing attention", "filter_attention")',
        "showAll": 'showAll = Button("Show all", "show_all", "secondary")',
    }


def respond(system: str, messages: list[dict]) -> str:
    prompt = last_user_text(messages)
    action = prompt[prompt.rfind("[ui action]"):] if "[ui action]" in prompt else ""
    if action:
        view = "attention" if "filter_attention" in action else "all"
        changed = program(view)
        return "\n".join(changed[k] for k in ("root", "names", "counts", "rows"))  # only what changes
    return "\n".join(program("all").values())


llm = get_llm(respond)
app = openui.make_app(HERE, LIBRARY, "OpenUI declarative")
session = {"gate": openui.StatementGate(LIBRARY)}


@app.post("/run")
def run(request):
    session["gate"] = openui.StatementGate(LIBRARY)
    yield from openui.generate(llm, SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}], session["gate"])


@app.post("/action")
def action(request):
    name = request.json.get("action")
    if name not in ("filter_attention", "show_all"):
        yield ("error", {"message": f"unknown action {name!r}"})
        return
    current = session["gate"].program.source()
    messages = [{"role": "user", "content": f"Current program:\n{current}\n\n[ui action] {name}"}]
    yield from openui.generate(llm, SYSTEM, messages, session["gate"])


if __name__ == "__main__":
    app.run(port_from_argv(8502))
