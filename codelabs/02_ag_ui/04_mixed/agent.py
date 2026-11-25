"""AG-UI, mixed mode: every AG-UI mechanism in one rebalancing desk.

* declarative: catalog elements in shared state (STATE_DELTA), as in step 02;
* open-ended:  one GeneratedView element whose HTML travels once as a CUSTOM
  event, not in state (state goes back and forth on every run);
* static:      a render tool, show_alert, drawn by a pre-built component;
* human in the loop: confirm_rebalance is a *frontend* tool. The page
  declares it in RunAgentInput.tools, the model calls it, the run ends, the
  operator answers, and the answer starts the next run as a tool message.
  Only then does the backend tool ``rebalance`` move any bikes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE.parent / "_shared")]

from genui_common import bikes  # noqa: E402
from genui_common.elements import CATALOG_V1, GENERATED_VIEW  # noqa: E402
from genui_common.llm import get_llm, last_user_text, text, tool, tool_results  # noqa: E402

CATALOG = CATALOG_V1.with_types(GeneratedView=GENERATED_VIEW)

TOOLS = [  # the agent's own tools; the page adds confirm_rebalance to every run
    {"name": "show_alert", "description": "Render tool: an alert banner.",
     "input_schema": {"type": "object", "properties": {"level": {"enum": ["info", "warning", "critical", "success"]},
                                                        "text": {"type": "string"}}, "required": ["level", "text"]}},
    {"name": "rebalance", "description": "Backend tool: move bikes. Only after the operator confirmed the plan.",
     "input_schema": {"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"},
                                                        "count": {"type": "integer", "minimum": 1}},
                      "required": ["from", "to", "count"]}},
]
RENDER_TOOLS, BACKEND_TOOLS = {"show_alert"}, {"rebalance"}


def system_for(state: dict) -> str:
    return f"""You run the rebalancing desk of a bike-share network.
To build or change the UI, write one JSON element per line: {{"id", "type", "props", "children"}}
(root id "desk"). Use catalog types for everything you can. For the interactive simulator use
one GeneratedView with props.artifact = "simulator", and on its own line write
{{"artifact": "simulator", "html": "<complete HTML document>"}} (inline CSS/JS, no network; it gets
data.stations via genui.onData and sends genui.send("rebalance", {{from, to, count}})).
Plain sentences are chat. Actions arrive as "[ui action] <name> <json>". Before moving bikes,
call the frontend tool confirm_rebalance with the plan; call rebalance only after it returns
confirmed=true. Elements in state: {sorted(state.get('ui', {}).get('elements', {})) or 'none'}.

{CATALOG.prompt()}"""


def layout(network: bikes.Network) -> list[dict]:
    summary = network.summary()
    return [
        {"id": "desk", "type": "Card", "props": {"title": "Rebalancing desk"}, "children": ["kpis", "sim", "help"]},
        {"id": "kpis", "type": "Row", "props": {}, "children": ["m_bikes", "m_attention"]},
        {"id": "m_bikes", "type": "Metric", "props": {"label": "Bikes docked", "value": f"{summary['bikes']} / {summary['capacity']}"}},
        {"id": "m_attention", "type": "Metric", "props": {"label": "Stations needing attention", "value": len(summary["needs_attention"])}},
        {"id": "sim", "type": "GeneratedView", "props": {"artifact": "simulator", "height": 250}},
        {"id": "help", "type": "Text", "props": {"text": "Plans need your confirmation before any bike moves.", "variant": "caption"}},
    ]


def respond(system: str, messages: list[dict]):
    results = tool_results(messages)
    if results:
        result = json.loads(results[0]["content"])
        if "confirmed" in result:
            if result["confirmed"]:
                return [tool("rebalance", result["plan"])]
            return [text("Understood, nothing was moved.")]
        if result.get("ok"):
            return [text(f"Done: moved {result['moved']} bikes from {result['from']} to {result['to']}.")]
        if "rendered" in result:
            return []
        return [text(f"The move failed: {result.get('error')}.")]
    prompt = last_user_text(messages)
    marker = prompt.rfind("[ui action] rebalance")
    if marker >= 0:
        plan = json.loads(prompt[marker:].split(" ", 3)[3])
        return [text("Please confirm this plan."), tool("confirm_rebalance", plan)]
    network = bikes.Network()
    lines = [json.dumps(e) for e in layout(network)]
    lines.append(json.dumps({"artifact": "simulator", "html": bikes.REBALANCE_SIMULATOR_HTML}))
    attention = ", ".join(network.get(i)["name"] for i in network.summary()["needs_attention"])
    return [text("Here is your rebalancing desk.\n" + "\n".join(lines) + "\n"),
            tool("show_alert", {"level": "warning", "text": f"Needs attention: {attention}."})]


def make_llm():
    return get_llm(respond)
