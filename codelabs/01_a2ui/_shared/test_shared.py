"""Tests for the A2UI theme's shared code: envelopes, catalog validation, client state."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

import a2ui  # noqa: E402
from genui_common.testing import run_node_tests  # noqa: E402


def test_mirror_validates_against_the_surface_catalog():
    mirror = a2ui.Mirror([a2ui.BASIC_CATALOG])
    assert mirror.apply(a2ui.create_surface("s")) == []
    bad = a2ui.update_components("s", [{"id": "root", "component": "Carousel", "items": []}])
    problems = mirror.apply(bad)
    assert problems and problems[0]["path"] == "/updateComponents/components/0"
    assert "unknown component" in problems[0]["message"]


def test_missing_required_prop_is_reported_with_a_path():
    mirror = a2ui.Mirror([a2ui.BASIC_CATALOG])
    mirror.apply(a2ui.create_surface("s"))
    problems = mirror.apply(a2ui.update_components("s", [{"id": "root", "component": "Button", "child": "x"}]))
    assert any("action" in p["message"] for p in problems)


def test_updates_before_create_are_errors():
    mirror = a2ui.Mirror([a2ui.BASIC_CATALOG])
    assert mirror.apply(a2ui.update_data_model("nope", "/", {}))[0]["message"] == "createSurface must come first"


def test_jsonl_splits_a_stream_into_messages():
    chunks = ['{"a":', '1}\n{"b"', ':2}\n```\n', '{"c":3}']
    assert list(a2ui.jsonl(chunks)) == ['{"a":1}', '{"b":2}', '{"c":3}']


def test_prompt_lists_every_component():
    prompt = a2ui.BASIC_CATALOG.prompt()
    for name in a2ui.BASIC:
        assert f"- {name}(" in prompt


def test_client_surface_state_in_node():
    run_node_tests(HERE / "tests" / "surface.test.mjs")
