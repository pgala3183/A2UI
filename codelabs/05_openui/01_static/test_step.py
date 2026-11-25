"""Offline tests for OpenUI static mode: python -m pytest"""

import json

import server  # first: sets sys.path
import openui
from genui_common.llm import ScriptedLLM
from genui_common.web import Request
from openui_parse import Program, resolve

server.llm = ScriptedLLM(server.respond, delay=0)


def run(prompt):
    return list(server.run(Request("POST", "/run", {}, {}, json.dumps({"prompt": prompt}).encode())))


def test_prompt_shows_positional_signatures():
    assert "- StationCard(name: string, bikes: number, capacity: number, status?: string, hourly?: list)" in server.SYSTEM


def test_answer_is_one_valid_statement():
    out = run("How is the Ferry Building doing?")
    lines = [d["line"] for e, d in out if e == "line"]
    assert len(lines) == 1 and lines[0].startswith('root = StationCard("Ferry Building", 21, 23')
    assert out[-1] == ("note", {"statements": 1, "unresolved": []})


def test_positional_arguments_become_named_props():
    program = Program()
    program.add(next(d["line"] for e, d in run("How is Market St doing?") if e == "line"))
    props = resolve(program, server.LIBRARY)["props"]
    assert props["name"] == "Market St & 4th" and props["capacity"] == 22 and len(props["hourly"]) == 13


def test_the_gate_checks_types_and_enums():
    gate = openui.StatementGate(server.LIBRARY)
    assert "must be number" in gate.offer('root = StationCard("A", "three", 5)')[0]
    assert "must be one of" in gate.offer('root = AlertBanner("panic", "x")')[0]
    assert "unknown component" in gate.offer('root = Iframe("https://x")')[0]
    assert "needs" in gate.offer("root = RideQuote(30)")[0]
