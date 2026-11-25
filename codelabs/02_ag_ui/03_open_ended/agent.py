"""AG-UI, open-ended mode: the model writes HTML; AG-UI carries it.

There is no catalog. The model answers in text and puts a complete HTML
document in a fenced ```html block. The text streams as TEXT_MESSAGE_CONTENT
like any reply. When the fence closes, the agent checks the document and
sends it once more as a CUSTOM event, ``genui.html``, which the page mounts
in a sandboxed iframe. Clicks inside the frame come back as user messages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text, text, tool, tool_results  # noqa: E402

TOOLS = [{"name": "quote_ride", "description": "Backend tool: the official price of a ride, and a booking reference.",
          "input_schema": {"type": "object", "properties": {"minutes": {"type": "number", "minimum": 5, "maximum": 180},
                                                             "ebike": {"type": "boolean"}, "member": {"type": "boolean"}},
                           "required": ["minutes", "ebike", "member"], "additionalProperties": False}}]

SYSTEM = """You are the assistant of a bike-share app. When the user asks for something interactive,
reply with one sentence, then one complete HTML document in a ```html fenced block, then one sentence.
The document must use inline CSS and JS only: no external URLs, no network, no storage. It runs in a
sandboxed iframe with a bridge: genui.onData(fn) receives {pricing, message}; genui.send(name, payload)
sends an action. For a trip calculator, send "book_ride" with {minutes, ebike, member, cost}.
Actions arrive as user messages "[ui action] <name> <json>". For book_ride, call quote_ride with the
values and confirm the booking in one sentence using the price it returns."""


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if results:
        quote = json.loads(results[0]["content"])
        return [text(f"Booked {quote['reference']}: {quote['minutes']} minutes for ${quote['price']:.2f}.")]
    prompt = last_user_text(messages)
    marker = prompt.rfind("[ui action] book_ride")
    if marker >= 0:
        payload = json.loads(prompt[marker:].split(" ", 3)[3])
        return [tool("quote_ride", {k: payload[k] for k in ("minutes", "ebike", "member")})]
    return [text("Here is an interactive trip-cost calculator.\n\n```html\n" + bikes.TRIP_CALCULATOR_HTML
                 + "\n```\n\nMove the slider, then book: the price is confirmed by the server.")]


def make_llm():
    return get_llm(respond)
