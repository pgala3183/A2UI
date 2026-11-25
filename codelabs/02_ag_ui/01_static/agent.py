"""AG-UI, static mode: tool calls are components.

The frontend owns two pre-built components, a station card and an alert.
Each is exposed to the model as a tool. When the model "calls" one, AG-UI
streams the call (TOOL_CALL_START, TOOL_CALL_ARGS..., TOOL_CALL_END) and the
page renders it with the matching component while the arguments stream in.
A third tool, ``get_station``, is an ordinary backend tool: the server runs
it and streams the answer back as TOOL_CALL_RESULT.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.llm import get_llm, last_user_text, text, tool, tool_results  # noqa: E402

TOOLS = [
    {"name": "get_station", "description": "Backend tool: live numbers for one station.",
     "input_schema": {"type": "object", "properties": {"station_id": {"enum": [s["id"] for s in bikes.STATIONS]}},
                      "required": ["station_id"], "additionalProperties": False}},
    {"name": "show_station_card", "description": "Render tool: show the station card component to the user.",
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string"}, "bikes": {"type": "integer"}, "capacity": {"type": "integer"},
         "status": {"type": "string"}, "hours": {"type": "array", "items": {"type": "string"}},
         "hourly": {"type": "array", "items": {"type": "integer"}}},
         "required": ["name", "bikes", "capacity"], "additionalProperties": False}},
    {"name": "show_alert", "description": "Render tool: show an alert banner to the user.",
     "input_schema": {"type": "object", "properties": {"level": {"enum": ["info", "warning", "critical"]},
                                                        "text": {"type": "string"}},
                      "required": ["level", "text"], "additionalProperties": False}},
]
BACKEND_TOOLS = {"get_station"}
RENDER_TOOLS = {"show_station_card", "show_alert"}

SYSTEM = ("You help bike-share operators. First call get_station. Then answer in one sentence and call "
          "show_station_card with exactly the numbers it returned. If the status is not 'balanced', also call "
          "show_alert. Stations: " + ", ".join(f"{s['id']} = {s['name']}" for s in bikes.STATIONS))


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if not results:
        prompt = last_user_text(messages).lower()
        station = next((s for s in bikes.STATIONS if s["id"] in prompt or s["name"].lower() in prompt), bikes.STATIONS[0])
        return [text(f"Checking {station['name']}..."), tool("get_station", {"station_id": station["id"]})]
    data = json.loads(results[0]["content"])
    if "bikes" not in data:  # the result of a render tool: nothing more to say
        return []
    blocks = [text(f"{data['name']} has {data['bikes']} of {data['capacity']} bikes."),
              tool("show_station_card", {k: data[k] for k in ("name", "bikes", "capacity", "status", "hours", "hourly")})]
    if data["status"] != "balanced":
        blocks.append(tool("show_alert", {"level": "warning", "text": f"{data['name']} is {data['status']}: plan a rebalancing run."}))
    return blocks


def make_llm():
    return get_llm(respond)
