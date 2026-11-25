"""Tests for the OpenUI theme's shared code: the parser twins, the gate, the prompt."""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

import openui  # noqa: E402
from genui_common.testing import run_node_tests  # noqa: E402
from openui import p  # noqa: E402
from openui_parse import ParseError, Program, parse_statement, resolve, unparse  # noqa: E402

LIB = {"Card": {"description": "c", "params": [p("title", "string"), p("children", "list")]},
       "Text": {"description": "t", "params": [p("text", "text"), p("variant", "string", optional=True)]}}


def test_statements_round_trip_through_unparse():
    line = 'root = Card("A \\"quoted\\" title", [t, Text(3), {"k": [true, null]}])'
    sid, node = parse_statement(line)
    assert sid == "root" and parse_statement(f"root = {unparse(node)}") == (sid, node)


def test_errors_are_raised_for_bad_lines():
    for bad in ('Root = Text("x")', 'a = Text("x"', "a = Text(\"x\") extra", "a = @"):
        with pytest.raises(ParseError):
            parse_statement(bad)


def test_forward_references_and_overrides():
    program = Program()
    program.add('root = Card("A", [t])')
    assert resolve(program, LIB)["props"]["children"][0]["type"] == "__missing"
    program.add('t = Text("one")')
    program.add('t = Text("two")')
    assert resolve(program, LIB)["props"]["children"][0]["props"]["text"] == "two"


def test_prompt_lists_positional_signatures():
    assert "- Text(text: text, variant?: string) - t" in openui.prompt(LIB)


def test_gate_reports_unresolved_references_at_the_end():
    gate = openui.StatementGate(LIB)
    assert gate.offer('root = Card("A", [a, b])') == []
    assert gate.offer('a = Text("x")') == []
    assert gate.unresolved() == ["b"]


def test_parser_twin_in_node():
    run_node_tests(HERE / "tests" / "parse.test.mjs")
