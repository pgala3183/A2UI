"""Run the AG-UI open-ended codelab: HTML in the text stream, a CUSTOM event, a booking.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import agent
import server
from genui_common import demo, tokens


def main():
    srv, url = server.app.start()
    demo.section("1. Events of the first run (content deltas collapsed)")
    body = {"threadId": "t", "runId": "r1", "messages": [{"id": "1", "role": "user", "content": "trip-cost calculator"}]}
    events = [e for _, e in demo.post_sse(f"{url}/agent", body)]
    deltas = [e for e in events if e["type"] == "TEXT_MESSAGE_CONTENT"]
    for e in events:
        if e["type"] == "TEXT_MESSAGE_CONTENT":
            continue
        extra = ""
        if e["type"] == "TEXT_MESSAGE_END":
            text = "".join(d["delta"] for d in deltas)
            extra = f"after {len(deltas)} TEXT_MESSAGE_CONTENT events, {len(text)} chars ({tokens.count(text)} tokens)"
        if e["type"] == "CUSTOM":
            value = e["value"]
            extra = f"{e['name']} " + (f"artifact={value['artifact']} html={len(value['html'])} chars" if "html" in value
                                       else json.dumps(value["data"])[:70])
        print(f"  {e['type']:<20} {extra}")
    artifact = next(e["value"]["artifact"] for e in events if e["type"] == "CUSTOM" and e["name"] == "genui.html")

    demo.section("2. A click inside the frame becomes a user message; a backend tool prices it")
    body = {"threadId": "t", "runId": "r2", "state": {"artifact": artifact}, "messages": [
        {"id": "1", "role": "user", "content": "trip-cost calculator"},
        {"id": "2", "role": "user", "content": '[ui action] book_ride {"minutes": 30, "ebike": false, "member": true, "cost": 4.25}'}]}
    for _, e in demo.post_sse(f"{url}/agent", body):
        if e["type"] in ("TOOL_CALL_START", "TOOL_CALL_RESULT", "CUSTOM", "TEXT_MESSAGE_CONTENT"):
            print(f"  {e['type']:<20} {json.dumps({k: v for k, v in e.items() if k not in ('type', 'timestamp', 'messageId')})[:110]}")

    demo.section("3. In the browser")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            inner = page.frame_locator("iframe.genui-sandbox")
            inner.locator("#min").evaluate("el => { el.value = 30; el.dispatchEvent(new Event('input')); }")
            inner.locator("#member").check()
            print("  frame:", inner.locator("#cost").inner_text(), "for 30 min as a member")
            inner.locator("#book").click()
            page.wait_for_function("document.body.dataset.actions === '1'", timeout=30000)
            inner.locator("#msg").filter(has_text="Booked").wait_for(timeout=10000)
            print("  frame message:", inner.locator("#msg").inner_text())
            print("  chat:", page.locator(".bubble.assistant").last.inner_text())
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
