"""json-render declarative mode: a patch stream, gated by the catalog.

    python server.py            then open http://127.0.0.1:8402

POST /run     each complete line of the model's reply is one operation; the
              PatchGate applies it to a mirror spec and forwards it only if
              the spec still validates. Refused operations become notes.
POST /action  "refresh": the application answers with /state patches only;
              every element bound with $state updates, no element is resent.
"""

from __future__ import annotations

import json
import random

import agent
from genui_common import bikes, jsonpatch
from genui_common.web import App, port_from_argv
from jr import PatchGate, patch_lines

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="json-render declarative")
llm = agent.make_llm()
network = bikes.Network()
session = {"gate": PatchGate(agent.CATALOG)}


@app.post("/run")
def run(request):
    gate = session["gate"] = PatchGate(agent.CATALOG)
    chunks = (e["text"] for e in llm.stream(agent.SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}])
              if e["type"] == "text")
    for line in patch_lines(chunks):
        try:
            op = json.loads(line)
        except ValueError:
            yield ("refused", {"line": line[:80], "errors": ["not JSON"]})
            continue
        errors = gate.offer(op)
        if errors:
            yield ("refused", {"op": op, "errors": errors})
        else:
            yield ("patch", op)
    yield ("note", {"elements": len(gate.spec["elements"]), "valid": agent.CATALOG.check(gate.spec) == []})


@app.post("/action")
def action(request):
    body = request.json
    if body.get("action") != "refresh":
        yield ("error", {"message": f"unknown action {body.get('action')!r}"})
        return
    for s in network.stations:  # pretend time passed: a few rides happened
        s["rides_today"] += random.randint(1, 4)
    gate = session["gate"]
    new_state = agent.state(network)
    for op in jsonpatch.diff(gate.spec["state"], new_state, "/state"):
        if not gate.offer(op):
            yield ("patch", op)


if __name__ == "__main__":
    app.run(port_from_argv(8402))
