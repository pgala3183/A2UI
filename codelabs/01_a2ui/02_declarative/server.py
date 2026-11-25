"""A2UI declarative mode: stream, validate, correct, and answer actions.

    python server.py            then open http://127.0.0.1:8102

POST /run     the model's reply is split into lines as it streams; each line
              is validated and forwarded at once (progressive rendering). The
              first invalid line stops forwarding: the server withdraws what
              it sent, gives the errors to the model and asks again.
POST /action  submit_report: the application validates the form and answers
              with updateDataModel (and one updateComponents).
"""

from __future__ import annotations

import json
import re

import agent
import a2ui
from genui_common import bikes
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="A2UI declarative")
network = bikes.Network()
mirror = a2ui.Mirror([a2ui.BASIC_CATALOG])
llm = agent.make_llm()
ATTEMPTS = 3


def texts(events, sink: list):
    """Pass text chunks through and keep a copy of the whole reply."""
    for event in events:
        if event["type"] == "text":
            sink.append(event["text"])
            yield event["text"]


def generate(prompt: str):
    for surface in list(mirror.surfaces):  # a new answer starts from a clean page
        mirror.apply(a2ui.delete_surface(surface))
        yield a2ui.delete_surface(surface)
    conversation = [{"role": "user", "content": prompt}]
    for attempt in range(1, ATTEMPTS + 1):
        reply, created, failed = [], [], None
        lines = a2ui.jsonl(texts(llm.stream(agent.SYSTEM, conversation), reply))
        for line in lines:
            try:
                message = json.loads(line)
            except ValueError:
                failed = [{"path": "/", "message": f"line is not JSON: {line[:80]}"}]
            else:
                failed = mirror.apply(message) or None
            if failed:
                for _ in lines:  # read the rest of the reply so the model sees it whole
                    pass
                break
            if a2ui.kind(message) == "createSurface":
                created.append(message["createSurface"]["surfaceId"])
            yield message  # forwarded the moment it is complete and valid
        if not failed:
            yield ("note", {"attempt": attempt, "result": "valid"})
            return
        yield ("note", {"attempt": attempt, "errors": failed})
        for surface in created:  # withdraw the half-built surface
            mirror.apply(a2ui.delete_surface(surface))
            yield a2ui.delete_surface(surface)
        conversation += [
            {"role": "assistant", "content": "".join(reply)},
            {"role": "user", "content": "The reply failed validation. Fix it and send the complete reply again.\n"
                                        + json.dumps(failed)},
        ]
    yield ("error", {"message": f"no valid reply after {ATTEMPTS} attempts"})


@app.post("/run")
def run(request):
    yield from generate(request.json.get("prompt", ""))


def check_report(context: dict) -> list[str]:
    problems = []
    if not re.fullmatch(r"B-?\d{2,5}", str(context.get("bike") or "").strip(), re.I):
        problems.append("bike number looks like B-1234")
    if len(str(context.get("issue") or "").strip()) < 3:
        problems.append("describe the issue")
    if not any(s["name"] == context.get("station") for s in network.stations):
        problems.append("pick a known station")
    return problems


@app.post("/action")
def action(request):
    try:
        act = a2ui.parse_action(request.json)
    except ValueError as error:
        yield ("error", {"message": str(error)})
        return
    surface = act["surfaceId"]
    if act["name"] != "submit_report" or surface not in mirror.surfaces:
        yield ("error", {"message": f"action {act['name']!r} is not allowed"})
        return
    problems = check_report(act["context"])  # the click is a request, not a permission
    if problems:
        yield a2ui.update_data_model(surface, "/report/result", "Please fix: " + "; ".join(problems))
        return
    station = next(s["id"] for s in network.stations if s["name"] == act["context"]["station"])
    ticket = network.report(station, act["context"]["bike"].upper(), act["context"]["issue"])
    urgent = " Marked unsafe: the bike is locked remotely." if act["context"].get("urgent") else ""
    yield a2ui.update_data_model(surface, "/report/result", f"Ticket {ticket['ticket']} created.{urgent}")
    yield a2ui.update_components(surface, [{"id": "send_label", "component": "Text", "text": "Report another bike"}])
    yield a2ui.update_data_model(surface, "/report/bike", "")


if __name__ == "__main__":
    app.run(port_from_argv(8102))
