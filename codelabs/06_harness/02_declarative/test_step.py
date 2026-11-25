"""Offline tests for harness declarative mode: python -m pytest"""

import agent
from genui_common.elements import CATALOG_V1
from genui_common.llm import ScriptedLLM


def run():
    return list(agent.make_harness(ScriptedLLM(agent.respond, delay=0)).ask("Make me a rebalancing report"))


def test_first_render_fails_with_a_readable_error():
    events = run()
    first = [e for e in events if e["type"] == "tool_result" and e["name"] == "render_ui"][0]
    assert first["is_error"]
    assert "unknown type 'PieChart'" in first["content"] and "unknown child 'footer'" in first["content"]


def test_the_model_fixes_the_spec_and_only_the_valid_one_is_drawn():
    events = run()
    renders = [e for e in events if e["type"] == "tool_call" and e["name"] == "render_ui"]
    ui = [e for e in events if e["type"] == "ui"]
    assert len(renders) == 2 and len(ui) == 1
    assert CATALOG_V1.check_spec(ui[0]["spec"]) == []
    assert events[-1]["type"] == "done"


def test_schema_errors_are_caught_before_the_catalog():
    content, events, is_error = agent.make_registry(agent.bikes.Network()).get("render_ui").execute({"view": "x"})
    assert is_error and "spec" in content and not events
