"""json-render mixed mode: one spec, two renderers, two kinds of action.

    python server.py            then open http://127.0.0.1:8404
    GET /text                   the same spec, rendered for a terminal

POST /run     gated patch stream (catalog + HTML policy)
POST /action  rebalance from the artifact -> /state patches (setState never
              reaches the server: it runs in the browser)
"""

from __future__ import annotations

import json

import agent
from genui_common import bikes, jsonpatch
from genui_common.web import App, Response, port_from_argv
from jr import PatchGate, patch_lines
from render_text import render_text

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="json-render mixed")
llm = agent.make_llm()
network = bikes.Network()
session = {"gate": PatchGate(agent.CATALOG, extra_check=agent.html_policy)}


@app.post("/run")
def run(request):
    global network
    network = bikes.Network()
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
    gate = session["gate"]
    if body.get("action") != "rebalance" or gate.spec["elements"].get(body.get("element"), {}).get("type") != "HtmlArtifact":
        yield ("error", {"message": "only the simulator may send rebalance"})
        return
    ids = {s["id"] for s in network.stations}
    if params.get("from") not in ids or params.get("to") not in ids or params.get("from") == params.get("to"):
        result = {"ok": False, "error": "pick two different stations"}
    else:
        result = network.rebalance(params["from"], params["to"], params.get("count", 0))
    message = (f"Moved {result['moved']} bikes from {result['from']} to {result['to']}." if result["ok"]
               else f"Not applied: {result['error']}.")
    new_state = {**gate.spec["state"], **agent.state(network, message)}
    for op in jsonpatch.diff(gate.spec["state"], new_state, "/state"):
        if not gate.offer(op):
            yield ("patch", op)


@app.get("/text")
def text_view(request):
    return Response(render_text(session["gate"].spec))


if __name__ == "__main__":
    app.run(port_from_argv(8404))
