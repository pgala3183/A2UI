"""json-render open-ended mode: an HTML document streamed through patches.

    python server.py            then open http://127.0.0.1:8403

POST /run     patches pass the gate (catalog + HTML policy on completion)
POST /action  book_ride from inside the sandbox: priced by the server and
              answered with a /state/message patch the document displays
"""

from __future__ import annotations

import json

import agent
from genui_common import bikes
from genui_common.web import App, port_from_argv
from jr import PatchGate, patch_lines

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="json-render open-ended")
llm = agent.make_llm()
network = bikes.Network()
session = {"gate": PatchGate(agent.CATALOG, extra_check=agent.html_policy)}


@app.post("/run")
def run(request):
    gate = session["gate"] = PatchGate(agent.CATALOG, extra_check=agent.html_policy)
    chunks = (e["text"] for e in llm.stream(agent.SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}])
              if e["type"] == "text")
    for line in patch_lines(chunks):
        op = json.loads(line)
        errors = gate.offer(op)
        yield ("refused", {"op": op, "errors": errors}) if errors else ("patch", op)


@app.post("/action")
def action(request):
    body = request.json
    params = body.get("params") or {}
    if body.get("action") != "book_ride" or body.get("element") != "calc":
        yield ("error", {"message": "unknown action"})
        return
    minutes = params.get("minutes")
    if not isinstance(minutes, (int, float)) or not 5 <= minutes <= 180:
        message = "Not booked: minutes must be 5 to 180."
    else:
        price = network.ride_cost(minutes, bool(params.get("ebike")), bool(params.get("member")))
        message = f"Booked: {int(minutes)} min for ${price:.2f} (server price)."
    op = {"op": "add", "path": "/state/message", "value": message}
    if not session["gate"].offer(op):
        yield ("patch", op)


if __name__ == "__main__":
    app.run(port_from_argv(8403))
