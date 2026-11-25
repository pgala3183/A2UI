"""Offline tests for harness open-ended mode: python -m pytest"""

import os

os.environ["GENUI_TERMINAL_MIRROR"] = "0"

import agent  # noqa: E402
import server  # noqa: E402
from genui_common.llm import ScriptedLLM  # noqa: E402
from genui_common.web import Request  # noqa: E402

PROMPT = "Make me an interactive trip-cost calculator"


def harness():
    return agent.make_harness(ScriptedLLM(agent.respond, delay=0))


def test_render_html_pauses_for_permission():
    h = harness()
    events = list(h.ask(PROMPT))
    assert events[-1]["type"] == "permission_request" and events[-1]["name"] == "render_html"
    assert not [e for e in events if e["type"] == "ui"]
    assert list(h.ask("hello"))[0]["type"] == "error"  # nothing else runs while paused


def test_approve_renders_and_declares_actions():
    h = harness()
    request = list(h.ask(PROMPT))[-1]
    events = list(h.resume(request["id"], True))
    ui = next(e for e in events if e["type"] == "ui")
    assert ui["kind"] == "html" and ui["actions"] == ["book_ride"]
    assert h.allowed_actions == {"calc": {"book_ride"}}
    assert "Content-Security-Policy" in agent.ARTIFACTS["calc"]


def test_deny_tells_the_model():
    h = harness()
    request = list(h.ask(PROMPT))[-1]
    events = list(h.resume(request["id"], False))
    result = next(e for e in events if e["type"] == "tool_result")
    assert result["is_error"] and "denied" in result["content"]
    assert "will not show it" in "".join(e["text"] for e in events if e["type"] == "text")


def test_declared_action_runs_a_turn_and_pushes_data_back():
    h = harness()
    list(h.resume(list(h.ask(PROMPT))[-1]["id"], True))
    events = list(h.ui_action("calc", "book_ride", {"minutes": 40, "ebike": False, "member": False, "cost": 11}))
    assert [e["name"] for e in events if e["type"] == "tool_call"] == ["quote_ride", "send_to_view"]
    data = next(e for e in events if e["type"] == "ui")
    assert data["kind"] == "data" and data["data"]["message"] == "Booked: 40 min for $11.00 (server price)."


def test_undeclared_actions_are_refused():
    h = harness()
    list(h.resume(list(h.ask(PROMPT))[-1]["id"], True))
    assert list(h.ui_action("calc", "delete_account", {}))[0]["type"] == "error"


def test_policy_violations_are_error_results():
    tool = agent.make_registry(agent.bikes.Network()).get("render_html")
    content, events, is_error = tool.execute({"view": "x", "title": "x", "actions": [],
                                              "html": "<html><script>fetch('https://evil.example')</script></html>"})
    assert is_error and "content policy" in content and not events


def test_artifacts_are_served_with_a_sandbox_csp_header():
    h = harness()
    list(h.resume(list(h.ask(PROMPT))[-1]["id"], True))
    response = server.app.routes[("GET", "/artifacts/*")](Request("GET", "/artifacts/calc.html", {}, {}))
    assert response.headers["Content-Security-Policy"].startswith("sandbox allow-scripts")
    missing = server.app.routes[("GET", "/artifacts/*")](Request("GET", "/artifacts/../../secret.html", {}, {}))
    assert missing.status == 404
