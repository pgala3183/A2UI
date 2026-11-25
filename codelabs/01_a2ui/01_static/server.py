"""A2UI static mode: the server turns one tool call into A2UI messages.

    python server.py            then open http://127.0.0.1:8101

POST /run     the model picks a template; the server sends createSurface,
              updateComponents (the fixed template) and updateDataModel,
              then keeps streaming data-only updates ("live" bike counts).
POST /action  a Button's action; the application answers without a model.
"""

from __future__ import annotations

import os
import time

import agent  # sets sys.path for genui_common and the theme's _shared folder
import a2ui
from genui_common import bikes
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="A2UI static")
network = bikes.Network()
mirror = a2ui.Mirror([a2ui.BASIC_CATALOG])
llm = agent.make_llm()
TICKS = int(os.environ.get("A2UI_TICKS", "3"))
TICK_SECONDS = float(os.environ.get("A2UI_TICK_SECONDS", "0.8"))


def emit(message: dict) -> dict:
    """Every outgoing message is checked against the surface's catalog first."""
    problems = mirror.apply(message)
    if problems:
        raise ValueError(problems)
    return message


def station_data(station_id: str) -> dict:
    v = network.view(station_id)
    return {"id": v["id"], "name": v["name"], "bikes": v["bikes"], "docks": v["docks"],
            "rides": v["rides_today"], "status": f"Status: {v['status']}", "updated": f"Updated {a2ui.now()}"}


def network_data() -> dict:
    return {"summary": network.summary(),
            "stations": [{"name": s["name"], "bikes": f"{s['bikes']}/{s['capacity']}", "status": bikes.status(s)}
                         for s in network.stations]}


def show(args: dict):
    """The tool call becomes A2UI: structure once, then data."""
    template = args["template"]
    station_id = args.get("station_id") or bikes.STATIONS[0]["id"]
    surface = f"{template}:{station_id}" if template == "station_status" else template
    if surface in mirror.surfaces:  # asking again replaces the old surface
        yield emit(a2ui.delete_surface(surface))
    yield emit(a2ui.create_surface(surface))
    yield emit(a2ui.update_components(surface, agent.TEMPLATES[template]))
    if template == "station_status":
        yield emit(a2ui.update_data_model(surface, "/station", station_data(station_id)))
        # From here on only data moves. The layout above is never sent again.
        for tick in range(TICKS):
            time.sleep(TICK_SECONDS)
            s = network.get(station_id)
            s["bikes"] = max(0, min(s["capacity"], s["bikes"] + (1 if tick % 3 != 2 else -1)))
            s["rides_today"] += 1
            yield emit(a2ui.update_data_model(surface, "/station", station_data(station_id)))
    else:
        yield emit(a2ui.update_data_model(surface, "/", network_data()))


@app.post("/run")
def run(request):
    messages = [{"role": "user", "content": request.json.get("prompt", "")}]
    for event in llm.stream(agent.SYSTEM, messages, agent.TOOLS):
        if event["type"] == "text":
            yield ("text", {"text": event["text"]})
        elif event["type"] == "tool_end" and event["name"] == "show_template":
            yield from show(event["input"])


@app.post("/action")
def action(request):
    try:
        act = a2ui.parse_action(request.json)
    except ValueError as error:
        yield ("error", {"message": str(error)})
        return
    if act["name"] == "refresh" and act["surfaceId"] in mirror.surfaces:
        station_id = act["context"].get("stationId")
        if station_id not in {s["id"] for s in network.stations}:
            yield ("error", {"message": f"unknown station {station_id!r}"})
            return
        # Granular updates: two pointers, not the whole object.
        data = station_data(station_id)
        yield emit(a2ui.update_data_model(act["surfaceId"], "/station/bikes", data["bikes"]))
        yield emit(a2ui.update_data_model(act["surfaceId"], "/station/updated", data["updated"] + " (refreshed)"))
    else:
        yield ("error", {"message": f"action {act['name']!r} is not allowed here"})


if __name__ == "__main__":
    app.run(port_from_argv(8101))
