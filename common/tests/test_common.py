"""Tests for the shared plumbing in common/: python -m pytest common/tests"""

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pytest  # noqa: E402

from genui_common import elements, jsonpatch, sandbox, sse  # noqa: E402
from genui_common.llm import ScriptedLLM, last_user_text, text, tool, tool_results  # noqa: E402
from genui_common.testing import run_node_tests  # noqa: E402
from genui_common.web import App, Response  # noqa: E402


def test_scripted_llm_streams_text_and_tool_calls():
    llm = ScriptedLLM(lambda s, m: [text("hello world"), tool("pick", {"a": [1, 2, 3]}, id="t1")], delay=0)
    events = list(llm.stream("sys", [{"role": "user", "content": "hi"}]))
    assert "".join(e["text"] for e in events if e["type"] == "text") == "hello world"
    deltas = "".join(e["json"] for e in events if e["type"] == "tool_delta")
    assert json.loads(deltas) == {"a": [1, 2, 3]}
    assert events[-1]["stop_reason"] == "tool_use" and llm.calls[0]["system"] == "sys"


def test_message_helpers():
    msgs = [{"role": "user", "content": "q"}, {"role": "assistant", "content": [{"type": "text", "text": "a"}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": "r"}]}]
    assert last_user_text(msgs) == "q" and tool_results(msgs)[0]["content"] == "r"


def test_json_patch_add_replace_remove_and_append():
    doc = {"a": {"b": [1]}}
    doc = jsonpatch.apply_patch(doc, [{"op": "add", "path": "/a/b/-", "value": 2},
                                      {"op": "replace", "path": "/a/b/0", "value": 0},
                                      {"op": "add", "path": "/c", "value": {"d": 1}},
                                      {"op": "remove", "path": "/c/d"}])
    assert doc == {"a": {"b": [0, 2]}, "c": {}}


def test_json_patch_refuses_prototype_keys_and_bad_indices():
    with pytest.raises(jsonpatch.PatchError):
        jsonpatch.apply_patch({}, [{"op": "add", "path": "/__proto__/x", "value": 1}])
    with pytest.raises(jsonpatch.PatchError):
        jsonpatch.apply_patch({"l": []}, [{"op": "add", "path": "/l/5", "value": 1}])


def test_diff_produces_a_patch_that_round_trips():
    old = {"ui": {"title": "A", "rows": [1]}, "gone": 1}
    new = {"ui": {"title": "B", "rows": [1, 2]}, "added": True}
    assert jsonpatch.apply_patch(old, jsonpatch.diff(old, new)) == new


def test_sandbox_policy_and_csp():
    assert sandbox.check_html("<html><body><b>ok</b></body></html>") == []
    problems = sandbox.check_html('<script src="x.js"></script><script>localStorage.x=1</script>')
    assert "external <script src> is not allowed" in problems and "storage access is not allowed" in problems
    html = sandbox.inject_csp("<html><head><title>t</title></head></html>")
    assert html.index("Content-Security-Policy") < html.index("<title>")


def test_element_catalog_catches_shape_errors():
    spec = {"root": "a", "elements": {"a": {"type": "Card", "props": {}, "children": ["b", "zz"]},
                                      "b": {"type": "Metric", "props": {"label": "x"}}}}
    errors = elements.CATALOG_V1.check_spec(spec)
    assert any("unknown child 'zz'" in e for e in errors) and any("'value' is a required" in e for e in errors)


def test_sse_frames_round_trip():
    body = sse.frame({"a": 1}) + sse.frame({"b": 2}, event="note")
    assert sse.parse(body) == [(None, {"a": 1}), ("note", {"b": 2})]


def test_web_app_serves_json_sse_static_and_refuses_traversal(tmp_path):
    (tmp_path / "index.html").write_text("<p>page</p>")
    app = App(tmp_path)
    app.post("/echo")(lambda r: r.json)
    app.post("/stream")(lambda r: (x for x in [{"n": 1}, ("note", {"n": 2})]))
    app.get("/plain")(lambda r: Response("hi"))
    srv, url = app.start()
    try:
        post = lambda path, body: urllib.request.urlopen(urllib.request.Request(url + path, json.dumps(body).encode(), method="POST")).read().decode()
        assert json.loads(post("/echo", {"x": 1})) == {"x": 1}
        assert sse.parse(post("/stream", {})) == [(None, {"n": 1}), ("note", {"n": 2})]
        assert urllib.request.urlopen(url + "/").read() == b"<p>page</p>"
        assert b"createShell" in urllib.request.urlopen(url + "/common/shell.mjs").read()
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url + "/common/../genui_common/llm.py")
    finally:
        srv.shutdown()


def test_browser_modules_in_node():
    run_node_tests(HERE / "web.test.mjs")
