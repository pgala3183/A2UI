"""Tests for the AG-UI theme's shared code: event builders and RunAgentInput handling."""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

import agui  # noqa: E402
from genui_common.llm import ScriptedLLM, text, tool  # noqa: E402


def every_event():
    return [agui.run_started("t", "r"), agui.step_started("s"), agui.text_start("m"), agui.text_content("m", "hi"),
            agui.text_end("m"), agui.tool_start("c", "show", "m"), agui.tool_args("c", "{}"), agui.tool_end("c"),
            agui.tool_result("c", {"ok": True}), agui.state_snapshot({"a": 1}),
            agui.state_delta([{"op": "add", "path": "/b", "value": 2}]), agui.custom("x", {"y": 1}),
            agui.step_finished("s"), agui.run_finished("t", "r"), agui.run_error("boom")]


def test_events_use_camel_case_fields():
    started = agui.run_started("t", "r")
    assert started["threadId"] == "t" and started["runId"] == "r" and "thread_id" not in started


def test_every_event_matches_the_official_models():
    core = pytest.importorskip("ag_ui.core")
    from pydantic import TypeAdapter

    adapter = TypeAdapter(core.Event)
    for event in every_event():
        assert type(adapter.validate_python(event)).__name__.upper().startswith(event["type"].replace("_", "")[:4])


def test_run_input_converts_history_to_messages_api_turns():
    run = agui.RunInput({"messages": [
        {"id": "1", "role": "user", "content": "hi"},
        {"id": "2", "role": "assistant", "content": "calling", "toolCalls": [
            {"id": "c1", "type": "function", "function": {"name": "get", "arguments": '{"a": 1}'}}]},
        {"id": "3", "role": "tool", "toolCallId": "c1", "content": "42"},
        {"id": "4", "role": "user", "content": "thanks"}]})
    turns = run.anthropic_messages()
    assert [t["role"] for t in turns] == ["user", "assistant", "user"]
    assert turns[1]["content"][1] == {"type": "tool_use", "id": "c1", "name": "get", "input": {"a": 1}}
    assert [b["type"] for b in turns[2]["content"]] == ["tool_result", "text"]


def test_bad_roles_are_refused():
    with pytest.raises(ValueError):
        agui.RunInput({"messages": [{"id": "1", "role": "admin", "content": "x"}]})


def test_model_events_close_text_before_a_tool_call():
    llm = ScriptedLLM(lambda s, m: [text("one moment"), tool("lookup", {"q": 1})], delay=0)
    kinds = [e["type"] for e, _ in agui.model_events(llm, "", []) if e]
    assert kinds.index("TEXT_MESSAGE_END") < kinds.index("TOOL_CALL_START")
    assert kinds[-1] == "TOOL_CALL_END"
