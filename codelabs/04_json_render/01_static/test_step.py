"""Offline tests for json-render static mode: python -m pytest"""

import json

import agent
import server
from genui_common.llm import ScriptedLLM
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)


def run(prompt):
    return list(server.run(Request("POST", "/run", {}, {}, json.dumps({"prompt": prompt}).encode())))


def test_prompt_lists_widgets_and_signatures():
    prompt = agent.CATALOG.prompt()
    assert "- StationCard(name, bikes, capacity, status?, hours?, hourly?)" in prompt
    assert "setState" in prompt  # the built-in action is always there


def test_wrong_prop_type_is_caught_then_fixed():
    out = run("How is Market St doing?")
    notes = [o[1] for o in out if o[0] == "note"]
    assert "is not of type 'integer'" in notes[0]["errors"][0]
    patch = next(o[1] for o in out if o[0] == "patch")
    assert patch["path"] == "" and patch["value"]["elements"]["w"]["props"]["bikes"] == 3


def test_one_widget_only():
    two = {"root": "a", "elements": {"a": {"type": "AlertBanner", "props": {"level": "info", "text": "x"}},
                                     "b": {"type": "AlertBanner", "props": {"level": "info", "text": "y"}}}}
    server.llm = ScriptedLLM(lambda s, m: json.dumps(two), delay=0)
    try:
        out = run("anything")
    finally:
        server.llm = ScriptedLLM(agent.respond, delay=0)
    assert out[-1][0] == "error"


def test_unknown_widgets_and_props_are_rejected():
    assert "unknown component" in agent.CATALOG.check({"root": "w", "elements": {"w": {"type": "PieChart", "props": {}}}})[0]
    errors = agent.CATALOG.check({"root": "w", "elements": {"w": {"type": "AlertBanner",
                                                                  "props": {"level": "info", "text": "x", "html": "<b>"}}}})
    assert "Additional properties" in errors[0]


def test_ride_question_picks_the_quote_widget():
    patch = next(o[1] for o in run("How much is a 30 minute ride?") if o[0] == "patch")
    assert patch["value"]["elements"]["w"] == {"type": "RideQuote", "props": {"minutes": 30, "ebike": False, "price": 8.5}}
