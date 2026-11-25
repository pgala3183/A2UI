"""Offline tests for A2UI static mode. No model, no network: python -m pytest"""

import agent
import a2ui
import server
from genui_common.llm import ScriptedLLM
from genui_common.web import Request

server.llm = ScriptedLLM(agent.respond, delay=0)
server.TICK_SECONDS = 0


def run(prompt):
    return list(server.run(Request("POST", "/run", {}, {}, f'{{"prompt": "{prompt}"}}'.encode())))


def a2ui_messages(frames):
    return [f for f in frames if isinstance(f, dict)]


def test_templates_are_valid_basic_catalog_components():
    for name, components in agent.TEMPLATES.items():
        ids = {c["id"] for c in components}
        assert "root" in ids, name
        for component in components:
            assert a2ui.BASIC_CATALOG.check(component) == [], (name, component)
            for child in [component.get("child"), *component.get("children", [])]:
                assert child is None or child in ids, (name, child)


def test_the_model_only_selects_a_template():
    events = list(server.llm.stream(agent.SYSTEM, [{"role": "user", "content": "How is the Ferry Building doing?"}], agent.TOOLS))
    calls = [e for e in events if e["type"] == "tool_end"]
    assert [c["input"] for c in calls] == [{"template": "station_status", "station_id": "ferry"}]


def test_structure_is_sent_once_then_only_data():
    messages = a2ui_messages(run("How is Market St doing?"))
    kinds = [a2ui.kind(m) for m in messages]
    assert kinds[:3] == ["createSurface", "updateComponents", "updateDataModel"]
    assert kinds.count("updateComponents") == 1
    assert set(kinds[3:]) == {"updateDataModel"} and len(kinds[3:]) == server.TICKS


def test_asking_again_replaces_the_surface():
    run("How is Market St doing?")
    kinds = [a2ui.kind(m) for m in a2ui_messages(run("How is Market St doing?"))]
    assert kinds[0] == "deleteSurface" and kinds[1] == "createSurface"


def test_refresh_action_returns_granular_data_updates():
    run("How is Market St doing?")
    body = {"version": "v0.9", "action": {"name": "refresh", "surfaceId": "station_status:market",
                                          "sourceComponentId": "refresh", "context": {"stationId": "market"}}}
    out = list(server.action(Request("POST", "/action", {}, {}, a2ui.compact(body).encode())))
    paths = [m["updateDataModel"]["path"] for m in out]
    assert paths == ["/station/bikes", "/station/updated"]


def test_unknown_actions_are_refused():
    body = {"version": "v0.9", "action": {"name": "delete_everything", "surfaceId": "x", "sourceComponentId": "y"}}
    out = list(server.action(Request("POST", "/action", {}, {}, a2ui.compact(body).encode())))
    assert out[0][0] == "error"


def test_page_is_served():
    srv, url = server.app.start()
    try:
        import urllib.request

        html = urllib.request.urlopen(url + "/").read().decode()
        shared = urllib.request.urlopen(url + "/shared/surface.mjs").read().decode()
        assert "app.mjs" in html and "class Processor" in shared
    finally:
        srv.shutdown()
