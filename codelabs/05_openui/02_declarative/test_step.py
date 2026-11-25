"""Offline tests for OpenUI declarative mode: python -m pytest"""

import json

import server  # first: sets sys.path
from genui_common.llm import ScriptedLLM
from genui_common.testing import run_node_tests
from genui_common.web import Request
from openui_parse import Program, resolve

server.llm = ScriptedLLM(server.respond, delay=0)


def post(handler, body):
    return list(handler(Request("POST", "/", {}, {}, json.dumps(body).encode())))


def test_root_comes_first_and_everything_resolves_at_the_end():
    out = post(server.run, {"prompt": "dashboard"})
    lines = [d["line"] for e, d in out if e == "line"]
    assert lines[0].startswith("root = Card(")
    assert out[-1] == ("note", {"statements": 13, "unresolved": []})


def test_forward_references_resolve_to_skeletons_until_defined():
    program = Program()
    program.add('root = Card("T", [kpis, chart])')
    tree = resolve(program, server.LIBRARY)
    assert [c["type"] for c in tree["props"]["children"]] == ["__missing", "__missing"]
    program.add('kpis = Stack([], "row")')
    assert resolve(program, server.LIBRARY)["props"]["children"][0]["type"] == "Stack"


def test_action_resends_only_changed_statements_and_they_replace():
    post(server.run, {"prompt": "dashboard"})
    out = post(server.action, {"action": "filter_attention"})
    ids = [d["line"].split(" =")[0] for e, d in out if e == "line"]
    assert ids == ["root", "names", "counts", "rows"]
    program = server.session["gate"].program
    assert len(program.statements) == 13  # replaced, not added
    tree = resolve(program, server.LIBRARY)
    assert tree["props"]["title"] == "Stations needing attention"


def test_unknown_actions_are_refused():
    assert post(server.action, {"action": "drop"})[0][0] == "error"


def test_parser_twin_in_node():
    run_node_tests(server.HERE.parent / "_shared" / "tests" / "parse.test.mjs")
