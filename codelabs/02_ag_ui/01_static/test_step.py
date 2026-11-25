"""Offline tests for AG-UI static mode: python -m pytest"""

import json

import pytest

import agent
import server
from genui_common.llm import ScriptedLLM
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)


def run(messages):
    body = {"threadId": "t", "runId": "r", "messages": messages}
    return list(server.run_agent(Request("POST", "/agent", {}, {}, json.dumps(body).encode())))


def types(events):
    return [e["type"] for e in events]


def test_a_run_is_framed_by_started_and_finished():
    events = run([{"id": "1", "role": "user", "content": "How is Market St doing?"}])
    assert events[0]["type"] == "RUN_STARTED" and events[-1]["type"] == "RUN_FINISHED"


def test_backend_tool_result_then_render_tools():
    events = run([{"id": "1", "role": "user", "content": "How is Market St doing?"}])
    starts = [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"]
    assert starts == ["get_station", "show_station_card", "show_alert"]  # Market St is nearly empty
    first_result = next(e for e in events if e["type"] == "TOOL_CALL_RESULT")
    assert json.loads(first_result["content"])["name"] == "Market St & 4th"


def test_args_stream_in_fragments_that_join_to_valid_json():
    events = run([{"id": "1", "role": "user", "content": "How is the Ferry Building doing?"}])
    card = next(e for e in events if e["type"] == "TOOL_CALL_START" and e["toolCallName"] == "show_station_card")
    fragments = [e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS" and e["toolCallId"] == card["toolCallId"]]
    assert len(fragments) > 3
    args = json.loads("".join(fragments))
    assert args["name"] == "Ferry Building" and args["bikes"] == 21


def test_invalid_render_args_come_back_as_an_error_result():
    content, is_error = server.run_tool({"name": "show_alert", "input": {"level": "panic"}})
    assert is_error and "panic" in content


def test_history_with_tool_calls_round_trips():
    first = run([{"id": "1", "role": "user", "content": "How is Market St doing?"}])
    calls = [e for e in first if e["type"] == "TOOL_CALL_START"]
    history = [{"id": "1", "role": "user", "content": "How is Market St doing?"},
               {"id": "2", "role": "assistant", "content": "", "toolCalls": [
                   {"id": c["toolCallId"], "type": "function", "function": {"name": c["toolCallName"], "arguments": "{}"}}
                   for c in calls]}]
    history += [{"id": f"r{i}", "role": "tool", "toolCallId": c["toolCallId"], "content": "{}"} for i, c in enumerate(calls)]
    history.append({"id": "9", "role": "user", "content": "And Caltrain Depot?"})
    events = run(history)
    assert "Caltrain Depot" in json.dumps(events)


def test_events_match_the_official_ag_ui_models():
    core = pytest.importorskip("ag_ui.core")
    from pydantic import TypeAdapter

    adapter = TypeAdapter(core.Event)
    for event in run([{"id": "1", "role": "user", "content": "How is Market St doing?"}]):
        adapter.validate_python(event)
