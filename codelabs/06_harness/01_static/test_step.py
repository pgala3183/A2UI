"""Offline tests for harness static mode: python -m pytest"""

import io

import agent
from genui_common.llm import ScriptedLLM
from harness.terminal import TerminalSurface
from rich.console import Console


def harness():
    return agent.make_harness(ScriptedLLM(agent.respond, delay=0))


def test_loop_runs_data_tool_then_render_tools_then_answers():
    events = list(harness().ask("Which stations need rebalancing?"))
    calls = [e["name"] for e in events if e["type"] == "tool_call"]
    assert calls == ["query_stations", "show_metric", "show_metric", "show_chart", "show_table"]
    assert events[-1] == {"type": "done", "reason": "end_turn"}


def test_render_tools_emit_ui_events_and_short_results():
    events = list(harness().ask("Which stations need rebalancing?"))
    ui = [e for e in events if e["type"] == "ui"]
    assert [u["component"] for u in ui] == ["Metric", "Metric", "BarChart", "Table"]
    assert len({u["view"] for u in ui}) == 4
    results = [e["content"] for e in events if e["type"] == "tool_result" and e["name"] == "show_table"]
    assert results == ["displayed a table with 3 rows"]  # the model reads a summary, not the UI


def test_invalid_render_input_is_an_error_result():
    content, events, is_error = agent.make_registry(agent.bikes.Network()).get("show_chart").execute({"title": "x"})
    assert is_error and "labels" in content and events == []


def test_terminal_surface_draws_the_same_events():
    out = io.StringIO()
    surface = TerminalSurface(Console(file=out, width=100, color_system=None))
    for event in harness().ask("Which stations need rebalancing?"):
        surface.handle(event)
    text = out.getvalue()
    assert "Stations needing rebalancing" in text and "Ferry Building" in text and "####" in text
    text.encode("ascii")  # ASCII only: safe on every console


def test_history_has_tool_results_for_every_call():
    h = harness()
    list(h.ask("Which stations need rebalancing?"))
    uses = [b["id"] for m in h.messages if m["role"] == "assistant" for b in m["content"] if b["type"] == "tool_use"]
    results = [b["tool_use_id"] for m in h.messages if m["role"] == "user" and isinstance(m["content"], list) for b in m["content"]]
    assert uses == results
