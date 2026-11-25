"""Tests for the json-render theme's shared code: catalog, patch gate, stream compiler."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

from genui_common.testing import run_node_tests  # noqa: E402
from jr import PRIMITIVES, Catalog, PatchGate, patch_lines  # noqa: E402

CATALOG = Catalog(PRIMITIVES, actions={"refresh": {"description": "r", "params": {}}})


def test_prompt_names_components_actions_and_bindings():
    prompt = CATALOG.prompt()
    assert "- Metric(label, value, delta?)" in prompt and "$state" in prompt and "- refresh()" in prompt


def test_state_bindings_are_valid_props():
    element = {"type": "Metric", "props": {"label": "Bikes", "value": {"$state": "/summary/bikes"}}}
    assert CATALOG.check_element("m", element) == []
    element["props"]["value"] = {"$state": "no-slash"}
    assert CATALOG.check_element("m", element)


def test_gate_keeps_only_operations_that_leave_a_valid_spec():
    gate = PatchGate(CATALOG)
    assert gate.offer({"op": "add", "path": "/root", "value": "a"}) == []
    assert gate.offer({"op": "add", "path": "/elements/a", "value": {"type": "Text", "props": {"text": "hi"}}}) == []
    assert gate.offer({"op": "replace", "path": "/elements/a/props/text", "value": ["not", "text"]})
    assert gate.spec["elements"]["a"]["props"]["text"] == "hi"  # the bad replace was not applied
    assert gate.offer({"op": "add", "path": "/secrets", "value": 1})
    assert gate.offer({"op": "move", "from": "/root", "path": "/x"})


def test_patch_lines_skip_fences_and_blanks():
    assert list(patch_lines(['```json\n{"op":"add",', '"path":"/root","value":"a"}\n\n```'])) == ['{"op":"add","path":"/root","value":"a"}']


def test_stream_compiler_in_node():
    run_node_tests(HERE / "tests" / "stream.test.mjs")
