"""Run the AG-UI static codelab and print the event stream.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import agent
import server
from genui_common import demo


def main():
    srv, url = server.app.start()
    demo.section("1. One run on the wire (RunAgentInput in, events out)")
    body = {"threadId": "t1", "runId": "r1", "state": {}, "tools": [], "context": [], "forwardedProps": {},
            "messages": [{"id": "m1", "role": "user", "content": "How is Market St doing?"}]}
    args = 0
    for _, event in demo.post_sse(f"{url}/agent", body):
        if event["type"] == "TOOL_CALL_ARGS":
            args += 1
            continue
        if args:
            print(f"  TOOL_CALL_ARGS x{args} (the arguments, streamed as JSON fragments)")
            args = 0
        detail = {k: v for k, v in event.items() if k not in ("type", "timestamp")}
        print(f"  {event['type']:<22} {str(detail)[:110]}")

    demo.section("2. In the browser: components drawn from tool calls")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            for slot in page.query_selector_all(".tool-ui"):
                print(f"  {slot.get_attribute('data-tool')}: {slot.inner_text()[:90].replace(chr(10), ' | ')}")
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
