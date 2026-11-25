"""Run the A2UI static codelab end to end and print what crosses the wire.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import agent
import server
from genui_common import demo


def main():
    demo.section("1. The model's whole job: one tool call")
    events = list(server.llm.stream(agent.SYSTEM, [{"role": "user", "content": "How is Market St doing?"}], agent.TOOLS))
    call = next(e for e in events if e["type"] == "tool_end")
    demo.show({"tool": call["name"], "input": call["input"]})

    srv, url = server.app.start()
    demo.section("2. The A2UI stream for that call")
    frames = demo.post_sse(f"{url}/run", {"prompt": "How is Market St doing?"})
    sizes = {}
    for event, data in frames:
        if event == "text":
            continue
        kind = next(k for k in data if k != "version")
        sizes[kind] = sizes.get(kind, 0) + len(json.dumps(data))
        demo.show(data, 140)
    print(f"  bytes by message type: {sizes}")
    print("  the layout was sent once; every later message carried data only")

    demo.section("3. A button action, answered by the application")
    envelope = {"version": "v0.9", "action": {"name": "refresh", "surfaceId": "station_status:market",
                                              "sourceComponentId": "refresh", "timestamp": "2026-11-24T12:00:00Z",
                                              "context": {"stationId": "market"}}}
    for event, data in demo.post_sse(f"{url}/action", envelope):
        demo.show(data)

    demo.section("4. In the browser")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            print("  surface text:", page.inner_text("[data-surface]").replace("\n", " | ")[:160])
            page.click("[data-surface] button")
            page.wait_for_function("document.body.dataset.runs === '1' && [...document.querySelectorAll('.wire-item')].some(li => li.textContent.includes('refreshed'))", timeout=15000)
            print("  after Refresh:", page.inner_text("[data-key=updated]"))
            print("  wire log entries:", page.eval_on_selector_all(".wire-item b", "els => els.map(e => e.textContent).join(', ')"))
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
