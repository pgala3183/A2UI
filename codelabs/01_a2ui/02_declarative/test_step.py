"""Offline tests for A2UI declarative mode: python -m pytest"""

import json

import agent
import a2ui
import server
from genui_common.llm import ScriptedLLM
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_prompt_is_built_from_the_catalog():
    for name in a2ui.BASIC:
        assert f"- {name}(" in agent.SYSTEM
    assert "submit_report" in agent.SYSTEM


def test_first_attempt_fails_validation_and_is_withdrawn():
    out = post(server.run, {"prompt": "broken bike"})
    notes = [o[1] for o in out if isinstance(o, tuple) and o[0] == "note"]
    assert "Dropdown" in notes[0]["errors"][0]["message"]
    assert notes[0]["errors"][0]["path"] == "/updateComponents/components/4"
    kinds = [a2ui.kind(o) for o in out if isinstance(o, dict)]
    # attempt 1 painted two messages, then the surface was withdrawn and rebuilt
    assert kinds[:3] == ["createSurface", "updateComponents", "deleteSurface"]
    assert notes[-1] == {"attempt": 2, "result": "valid"}


def test_the_correction_turn_contains_the_errors():
    server.llm.calls.clear()
    post(server.run, {"prompt": "broken bike"})
    second = server.llm.calls[1]["messages"]
    assert second[-2]["role"] == "assistant" and "Dropdown" in second[-2]["content"]
    assert "failed validation" in second[-1]["content"]


def test_every_forwarded_message_is_valid_in_a_fresh_mirror():
    server.mirror.surfaces.clear()  # start from an empty page
    out = post(server.run, {"prompt": "broken bike"})
    mirror = a2ui.Mirror([a2ui.BASIC_CATALOG])
    for message in (o for o in out if isinstance(o, dict)):
        assert mirror.apply(message) == []


def action(context):
    return {"version": "v0.9", "action": {"name": "submit_report", "surfaceId": agent.SURFACE,
                                          "sourceComponentId": "send", "context": context}}


def test_action_with_bad_input_gets_a_data_model_answer():
    post(server.run, {"prompt": "broken bike"})
    out = post(server.action, action({"station": "Market St & 4th", "bike": "", "issue": ""}))
    assert out[0]["updateDataModel"]["path"] == "/report/result"
    assert "bike number" in out[0]["updateDataModel"]["value"]


def test_valid_action_creates_a_ticket():
    post(server.run, {"prompt": "broken bike"})
    out = post(server.action, action({"station": "Market St & 4th", "bike": "b-2231", "issue": "flat tyre", "urgent": True}))
    assert out[0]["updateDataModel"]["value"].startswith("Ticket BK-")
    assert "locked" in out[0]["updateDataModel"]["value"]
    assert out[1]["updateComponents"]["components"][0]["id"] == "send_label"
    assert server.network.tickets[-1]["bike"] == "B-2231"


def test_actions_not_in_the_prompt_are_refused():
    post(server.run, {"prompt": "broken bike"})
    body = action({})
    body["action"]["name"] = "delete_all_tickets"
    assert post(server.action, body)[0][0] == "error"
