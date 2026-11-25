"""AG-UI open-ended mode: TEXT_MESSAGE_* for the reply, CUSTOM for the artifact.

    python server.py            then open http://127.0.0.1:8203

The agent watches the reply as it streams. When a ```html block is complete
it runs the content policy; right after TEXT_MESSAGE_END it emits CUSTOM
genui.html (or genui.html.rejected), then CUSTOM genui.data with the prices
the document should show. (AG-UI keeps one message's events together, so
the CUSTOM events wait for the text message to close.) A book_ride action
runs the backend tool quote_ride; its result goes to the model and, as
CUSTOM genui.data, into the iframe.
"""

from __future__ import annotations

import itertools
import json
import re

import agent
import agui
from genui_common import bikes
from genui_common.sandbox import check_html
from genui_common.web import App, port_from_argv

HERE = agent.HERE
app = App(HERE / "page", {"/shared/": HERE.parent / "_shared"}, title="AG-UI open-ended")
network = bikes.Network()
llm = agent.make_llm()
FENCE = re.compile(r"```html\s*\n(.*?)```", re.S)
references = itertools.count(301)


def quote(args: dict) -> dict:
    price = network.ride_cost(args["minutes"], args["ebike"], args["member"])
    return {**args, "price": price, "reference": f"RIDE-{next(references)}"}


@app.post("/agent")
def run_agent(request):
    run = agui.RunInput(request.json)
    yield agui.run_started(run.thread_id, run.run_id)
    messages = run.anthropic_messages()
    artifact = run.state.get("artifact")  # the page tells us which frame is on screen
    try:
        for _ in range(3):
            reply, sent, done, pending = "", False, None, []
            for event, final in agui.model_events(llm, agent.SYSTEM, messages, agent.TOOLS):
                if event is None:
                    done = final
                    continue
                yield event
                if event["type"] == "TEXT_MESSAGE_END":
                    yield from pending  # CUSTOM events go out once the text message is closed
                    pending = []
                if event["type"] == "TEXT_MESSAGE_CONTENT":
                    reply += event["delta"]
                    match = FENCE.search(reply)
                    if match and not sent:  # the document is complete: check it, then ship it
                        sent = True
                        html = match.group(1)
                        problems = check_html(html)
                        if problems:
                            pending.append(agui.custom("genui.html.rejected", {"problems": problems}))
                        else:
                            artifact = f"html_{run.run_id}"
                            pending.append(agui.custom("genui.html", {"artifact": artifact, "title": "Trip cost calculator", "html": html}))
                            pending.append(agui.custom("genui.data", {"artifact": artifact, "data": {"pricing": network.pricing}}))
            messages.append({"role": "assistant", "content": done["content"]})
            calls = [b for b in done["content"] if b["type"] == "tool_use"]
            if not calls:
                break
            results = []
            for call in calls:
                result = quote(call["input"])
                yield agui.tool_result(call["id"], result)
                if artifact:
                    message = f"Booked {result['reference']}: ${result['price']:.2f} (server price)"
                    yield agui.custom("genui.data", {"artifact": artifact, "data": {"pricing": network.pricing, "message": message}})
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": json.dumps(result)})
            messages.append({"role": "user", "content": results})
        yield agui.run_finished(run.thread_id, run.run_id)
    except Exception as error:
        yield agui.run_error(str(error))


if __name__ == "__main__":
    app.run(port_from_argv(8203))
