"""OpenUI Lang, static mode: one statement that picks a pre-built widget.

    python server.py            then open http://127.0.0.1:8501

The library holds three whole widgets. The model's entire answer is one
line, ``root = StationCard(...)``: it chooses the widget and fills its
positional arguments. Positional arguments are why OpenUI Lang is compact:
the parameter names live in the library, not in every reply.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

import openui  # noqa: E402
from openui import p  # noqa: E402
from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text  # noqa: E402
from genui_common.web import port_from_argv  # noqa: E402

LIBRARY = {
    "StationCard": {"description": "Everything about one station, with its hourly rides.",
                    "params": [p("name", "string"), p("bikes", "number"), p("capacity", "number"),
                               p("status", "string", optional=True), p("hourly", "list", optional=True)]},
    "AlertBanner": {"description": "One warning sentence.",
                    "params": [p("level", "string", enum=["info", "warning", "critical"]), p("text", "string")]},
    "RideQuote": {"description": "The price of one ride.", "params": [p("minutes", "number"), p("price", "number")]},
}
NETWORK = bikes.Network()
SYSTEM = (openui.prompt(LIBRARY) + "\nAnswer with exactly one statement, root = <one widget>(...). Data: "
          + "; ".join(f"{s['name']} {s['bikes']}/{s['capacity']} {bikes.status(s)} hourly={bikes.hourly(s['id'])}"
                      for s in NETWORK.stations) + ". Prices: $1 unlock + $0.25/min.")


def respond(system: str, messages: list[dict]) -> str:
    prompt = last_user_text(messages).lower()
    if "ride" in prompt and "minute" in prompt:
        return f"root = RideQuote(30, {NETWORK.ride_cost(30, False, False)})"
    s = next((v for v in NETWORK.stations if v["id"] in prompt or v["name"].lower() in prompt), NETWORK.stations[0])
    return f'root = StationCard("{s["name"]}", {s["bikes"]}, {s["capacity"]}, "{bikes.status(s)}", {bikes.hourly(s["id"])})'


llm = get_llm(respond)
app = openui.make_app(HERE, LIBRARY, "OpenUI static")


@app.post("/run")
def run(request):
    gate = openui.StatementGate(LIBRARY)
    yield from openui.generate(llm, SYSTEM, [{"role": "user", "content": request.json.get("prompt", "")}], gate)


if __name__ == "__main__":
    app.run(port_from_argv(8501))
