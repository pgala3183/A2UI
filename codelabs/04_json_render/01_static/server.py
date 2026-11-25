"""json-render static mode: one validated spec with one widget.

    python server.py            then open http://127.0.0.1:8401

The reply is a complete spec, so it is validated as a whole and sent as one
patch that replaces the page's spec (step 02 streams instead).
"""

from __future__ import annotations

import json

import agent
from genui_common.llm import reply_text
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="json-render static")
llm = agent.make_llm()


def generate(prompt: str, attempts: int = 2):
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(1, attempts + 1):
        reply, _ = reply_text(llm.stream(agent.SYSTEM, messages))
        try:
            spec = json.loads(reply)
            errors = agent.CATALOG.check(spec)
            if len(spec.get("elements", {})) != 1:
                errors.append("static mode: exactly one widget")
        except ValueError as error:
            spec, errors = None, [f"not JSON: {error}"]
        if not errors:
            yield ("note", {"attempt": attempt, "result": "valid"})
            yield ("patch", {"op": "replace", "path": "", "value": spec})
            return
        yield ("note", {"attempt": attempt, "errors": errors})
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "The reply failed validation: " + "; ".join(errors)}]
    yield ("error", {"message": "no valid spec"})


@app.post("/run")
def run(request):
    yield from generate(request.json.get("prompt", ""))


if __name__ == "__main__":
    app.run(port_from_argv(8401))
