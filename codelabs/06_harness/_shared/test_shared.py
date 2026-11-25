"""Tests for the harness itself: tools, the loop, permissions, declared actions."""

import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

from genui_common.llm import ScriptedLLM, text, tool, tool_results  # noqa: E402
from harness.loop import Harness  # noqa: E402
from harness.terminal import TerminalSurface  # noqa: E402
from harness.tools import Registry, ToolError, obj  # noqa: E402
from rich.console import Console  # noqa: E402


def make(permission="allow"):
    registry = Registry()

    @registry.add("echo", "Echo.", obj(["word"], word={"type": "string"}), permission=permission)
    def echo(word):
        if word == "boom":
            raise ToolError("no booms")
        return f"echo {word}", [{"type": "ui", "kind": "component", "view": "v", "component": "Text",
                                 "props": {"text": word}, "actions": ["again"]}]

    def respond(system, messages):
        results = tool_results(messages)
        if results:
            return [text(f"tool said: {results[0]['content']}")]
        return [tool("echo", {"word": messages[-1]["content"].split()[-1]})]

    return Harness(ScriptedLLM(respond, delay=0), "sys", registry)


def test_loop_runs_tools_and_answers():
    events = list(make().ask("say hi"))
    assert [e["type"] for e in events] == ["tool_call", "ui", "tool_result", "text", "done"]


def test_tool_errors_and_schema_errors_become_results():
    events = list(make().ask("say boom"))
    assert next(e for e in events if e["type"] == "tool_result")["is_error"]
    registry = make().registry
    content, _, is_error = registry.get("echo").execute({"word": 5})
    assert is_error and "not of type 'string'" in content


def test_ask_permission_pauses_and_resumes():
    h = make("ask")
    events = list(h.ask("say hi"))
    assert events[-1]["type"] == "permission_request"
    resumed = list(h.resume(events[-1]["id"], True))
    assert [e["type"] for e in resumed][:2] == ["ui", "tool_result"]  # not announced twice


def test_deny_permission_is_reported_to_the_model():
    h = make("ask")
    request = list(h.ask("say hi"))[-1]
    events = list(h.resume(request["id"], False))
    assert "denied" in "".join(e.get("text", "") for e in events)


def test_only_declared_actions_start_turns():
    h = make()
    list(h.ask("say hi"))
    assert list(h.ui_action("v", "again", {}))[0]["type"] == "tool_call"
    assert list(h.ui_action("v", "rm", {}))[0]["type"] == "error"


def test_terminal_surface_is_ascii():
    out = io.StringIO()
    surface = TerminalSurface(Console(file=out, width=80, color_system=None))
    for event in make("ask").ask("say hi"):
        surface.handle(event)
    out.getvalue().encode("ascii")
    assert "permission needed" in out.getvalue()
