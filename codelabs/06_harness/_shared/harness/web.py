"""The web surface: the harness's events over SSE, plus the two ways back in.

    POST /reset       a new session
    POST /run         {prompt}                      -> events of one turn
    POST /approve     {id, approve}                 -> the paused loop continues
    POST /ui-action   {view, action, params}        -> a new turn, if the view declared the action
    GET  /artifacts/<id>.html                        model-written HTML, served with a CSP *header*
                                                      that includes `sandbox`, so the page gets an
                                                      opaque origin even when opened directly

While the browser is the surface, the server's own terminal mirrors every
event with the terminal surface: one agent, two surfaces at the same time.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from genui_common.web import App, Response

from .terminal import TerminalSurface

SHARED = Path(__file__).resolve().parent.parent
HEADER_CSP = ("sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; "
              "style-src 'unsafe-inline'; img-src data:; connect-src 'none'")


def make_app(step_dir: Path, make_harness, title: str, artifacts: dict | None = None, mirror: bool | None = None):
    app = App(step_dir / "page", {"/shared/": SHARED}, title=title)
    state = {"harness": make_harness()}
    store = artifacts if artifacts is not None else {}
    if mirror is None:
        mirror = os.environ.get("GENUI_TERMINAL_MIRROR", "1") == "1"
    terminal = TerminalSurface() if mirror else None

    def relay(events):
        for event in events:
            if terminal:
                terminal.handle(event)
            yield event

    @app.post("/reset")
    def reset(request):
        state["harness"] = make_harness()
        return {"ok": True}

    @app.post("/run")
    def run(request):
        yield from relay(state["harness"].ask(request.json.get("prompt", "")))

    @app.post("/approve")
    def approve(request):
        body = request.json
        yield from relay(state["harness"].resume(body.get("id"), bool(body.get("approve"))))

    @app.post("/ui-action")
    def ui_action(request):
        body = request.json
        yield from relay(state["harness"].ui_action(str(body.get("view")), str(body.get("action")), body.get("params") or {}))

    @app.get("/artifacts/*")
    def artifact(request):
        match = re.fullmatch(r"/artifacts/([A-Za-z0-9_-]+)\.html", request.path)
        if not match or match.group(1) not in store:
            return Response("not found", status=404)
        return Response(store[match.group(1)], "text/html; charset=utf-8", headers={"Content-Security-Policy": HEADER_CSP})

    app.state = state
    return app
