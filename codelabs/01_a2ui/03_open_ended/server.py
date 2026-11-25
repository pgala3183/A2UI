"""A2UI open-ended mode: model-written HTML inside an A2UI surface.

    python server.py            then open http://127.0.0.1:8103

POST /run     forwards the model's messages after checking the HtmlFrame's
              HTML against the content policy; then, a moment later, the
              server changes the price through updateDataModel and the
              generated calculator recomputes. Open-ended does not mean
              disconnected: the data model still drives the view.
POST /action  book_ride from inside the iframe. The server recomputes the
              price itself; it never trusts the cost the frame sent.
"""

from __future__ import annotations

import json
import os
import time

import agent
import a2ui
from genui_common import bikes
from genui_common.web import App, port_from_argv
from htmlframe import OPEN_CATALOG

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="A2UI open-ended")
network = bikes.Network()
mirror = a2ui.Mirror([OPEN_CATALOG])
llm = agent.make_llm()
PEAK_DELAY = float(os.environ.get("A2UI_PEAK_DELAY", "1.5"))


@app.post("/run")
def run(request):
    for surface in list(mirror.surfaces):
        mirror.apply(a2ui.delete_surface(surface))
        yield a2ui.delete_surface(surface)
    network.pricing = dict(bikes.PRICING)
    chunks = (e["text"] for e in llm.stream(agent.SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}])
              if e["type"] == "text")
    for line in a2ui.jsonl(chunks):
        message = json.loads(line)
        problems = mirror.apply(message)  # includes the HTML content policy
        if problems:
            yield ("error", {"errors": problems})
            return
        yield message
    # The server pushes data into the generated view, exactly as for catalog components.
    time.sleep(PEAK_DELAY)
    network.pricing["per_minute"] = 0.30
    yield a2ui.update_data_model(agent.SURFACE, "/pricing/per_minute", 0.30)
    yield a2ui.update_data_model(agent.SURFACE, "/message", "Peak pricing is on: $0.30 per minute.")


def check_booking(context: dict) -> list[str]:
    problems = []
    if not isinstance(context.get("minutes"), (int, float)) or not 5 <= context["minutes"] <= 180:
        problems.append("minutes must be between 5 and 180")
    for flag in ("ebike", "member"):
        if not isinstance(context.get(flag), bool):
            problems.append(f"{flag} must be true or false")
    return problems


@app.post("/action")
def action(request):
    try:
        act = a2ui.parse_action(request.json)
    except ValueError as error:
        yield ("error", {"message": str(error)})
        return
    if act["name"] != "book_ride" or act["surfaceId"] not in mirror.surfaces:
        yield ("error", {"message": f"action {act['name']!r} is not allowed"})
        return
    ctx = act["context"]
    problems = check_booking(ctx)
    if problems:
        yield a2ui.update_data_model(act["surfaceId"], "/message", "Not booked: " + "; ".join(problems))
        return
    price = network.ride_cost(ctx["minutes"], ctx["ebike"], ctx["member"])  # the server's price, not the frame's
    note = "" if abs(price - float(ctx.get("cost") or 0)) < 0.01 else f" (the page showed ${float(ctx.get('cost') or 0):.2f})"
    kind = "e-bike" if ctx["ebike"] else "bike"
    yield a2ui.update_data_model(act["surfaceId"], "/message",
                                 f"Booked: {ctx['minutes']} min {kind} ride for ${price:.2f}{note}.")


if __name__ == "__main__":
    app.run(port_from_argv(8103))
