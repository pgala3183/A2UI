"""A2UI mixed mode: catalog components and an HtmlFrame on one data model.

    python server.py            then open http://127.0.0.1:8104

POST /run     the model's layout (validated against the mixed catalog), then
              the application's data: /summary, /stations, /message.
POST /action  two sources, one envelope: "refresh" from a catalog Button,
              "rebalance" from inside the sandboxed frame. The server checks
              both the same way and answers with data-model updates only, so
              the layout (and the live iframe) stay in place.
"""

from __future__ import annotations

import json

import agent
import a2ui
from genui_common import bikes
from genui_common.web import App, port_from_argv
from htmlframe import MIXED_CATALOG

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="A2UI mixed")
network = bikes.Network()
mirror = a2ui.Mirror([MIXED_CATALOG])
llm = agent.make_llm()


def data_updates(surface: str, message: str):
    summary = network.summary()
    names = [network.get(i)["name"] for i in summary["needs_attention"]]
    summary["attention"] = "Needs attention: " + (", ".join(names) if names else "nothing")
    stations = [{"id": s["id"], "name": s["name"], "bikes": s["bikes"], "capacity": s["capacity"]} for s in network.stations]
    yield a2ui.update_data_model(surface, "/summary", summary)
    yield a2ui.update_data_model(surface, "/stations", stations)
    yield a2ui.update_data_model(surface, "/message", message)


@app.post("/run")
def run(request):
    for surface in list(mirror.surfaces):
        mirror.apply(a2ui.delete_surface(surface))
        yield a2ui.delete_surface(surface)
    chunks = (e["text"] for e in llm.stream(agent.SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}])
              if e["type"] == "text")
    frames = 0
    for line in a2ui.jsonl(chunks):
        message = json.loads(line)
        problems = mirror.apply(message)
        if a2ui.kind(message) == "updateComponents":
            frames += sum(c.get("component") == "HtmlFrame" for c in message["updateComponents"]["components"])
            if frames > 1:
                problems.append({"path": "/updateComponents", "message": "at most one HtmlFrame per surface"})
        if problems:
            yield ("error", {"errors": problems})
            return
        yield message
    yield from data_updates(agent.SURFACE, "Pick two stations in the simulator and apply a plan.")


@app.post("/action")
def action(request):
    try:
        act = a2ui.parse_action(request.json)
    except ValueError as error:
        yield ("error", {"message": str(error)})
        return
    surface, ctx = act["surfaceId"], act["context"]
    if surface not in mirror.surfaces:
        yield ("error", {"message": "unknown surface"})
    elif act["name"] == "refresh" and act["sourceComponentId"] == "refresh":
        yield from data_updates(surface, f"Numbers refreshed at {a2ui.now()} UTC.")
    elif act["name"] == "rebalance" and act["sourceComponentId"] == "sim":
        ids = {s["id"] for s in network.stations}
        if ctx.get("from") not in ids or ctx.get("to") not in ids or ctx.get("from") == ctx.get("to"):
            yield from data_updates(surface, "Not applied: pick two different stations.")
            return
        result = network.rebalance(ctx["from"], ctx["to"], ctx.get("count", 0))
        text = (f"Moved {result['moved']} bikes from {result['from']} to {result['to']}." if result["ok"]
                else f"Not applied: {result['error']}.")
        yield from data_updates(surface, text)
    else:
        yield ("error", {"message": f"{act['name']!r} from {act['sourceComponentId']!r} is not allowed"})


if __name__ == "__main__":
    app.run(port_from_argv(8104))
