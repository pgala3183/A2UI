"""json-render, static mode: a catalog of whole widgets.

The catalog has three pre-built widgets and no layout primitives, so a spec
is exactly one element: the model chooses a widget and fills its props. The
same catalog produces the prompt, validates the reply, and (in the browser)
names the components the registry draws.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from catalog import Catalog  # noqa: E402
from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text  # noqa: E402

I, S = {"type": "integer"}, {"type": "string"}
CATALOG = Catalog(
    components={
        "StationCard": {"description": "Everything about one station, with an hourly chart.",
                        "props": {"name": S, "bikes": I, "capacity": I, "status": S,
                                  "hours": {"type": "array", "items": S}, "hourly": {"type": "array", "items": I}},
                        "required": ["name", "bikes", "capacity"]},
        "AlertBanner": {"description": "One warning sentence.",
                        "props": {"level": {"enum": ["info", "warning", "critical"]}, "text": S}, "required": ["level", "text"]},
        "RideQuote": {"description": "The price of one ride.",
                      "props": {"minutes": I, "ebike": {"type": "boolean"}, "price": {"type": "number"}},
                      "required": ["minutes", "price"]},
    },
    actions={},
)

NETWORK = bikes.Network()
DATA = {s["id"]: {**NETWORK.view(s["id"]), "hours": bikes.HOURS} for s in bikes.STATIONS}

SYSTEM = f"""You answer with one json-render spec and nothing else:
{{"root": "w", "elements": {{"w": {{"type": "<one widget>", "props": {{...}}}}}}}}
Pick exactly one widget from the catalog and fill its props from the data.
Ride prices: $1 unlock + $0.25/min (+$0.15/min e-bike).
Data: {json.dumps({k: {f: v[f] for f in ("name", "bikes", "capacity", "status")} for k, v in DATA.items()})}

{CATALOG.prompt()}"""


def respond(system: str, messages: list[dict]) -> str:
    prompt = last_user_text(messages).lower()
    retry = "failed validation" in prompt
    if "ride" in prompt and "minute" in prompt:
        widget = {"type": "RideQuote", "props": {"minutes": 30, "ebike": False, "price": NETWORK.ride_cost(30, False, False)}}
    else:
        s = next((v for k, v in DATA.items() if k in prompt or v["name"].lower() in prompt), DATA["market"])
        props = {"name": s["name"], "bikes": s["bikes"], "capacity": s["capacity"], "status": s["status"],
                 "hours": s["hours"], "hourly": s["hourly"]}
        if not retry:
            props["bikes"] = f"{s['bikes']} bikes"  # a typical first-attempt mistake: a string, not an integer
        widget = {"type": "StationCard", "props": props}
    return json.dumps({"root": "w", "elements": {"w": widget}})


def make_llm():
    return get_llm(respond)
