"""Run the OpenUI open-ended codelab: a long statement, progress, a policy, a booking.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import server  # first: sets sys.path
import openui
from genui_common import demo, tokens


def main():
    srv, url = server.app.start()
    demo.section("1. The stream: progress events while the document line grows")
    for event, data in demo.post_sse(f"{url}/run", {"prompt": "calculator"}):
        if event == "line":
            line = data["line"]
            print(f"  line     {line[:70]}{'...' if len(line) > 70 else ''}  ({len(line)} chars, {tokens.count(line)} tokens)")
        else:
            print(f"  {event:<8} {data}")

    demo.section("2. The policy runs on the document, whichever statement comes first")
    gate = openui.StatementGate(server.LIBRARY, extra_check=openui.artifact_policy)
    print("  ", gate.offer('root = HtmlArtifact("x", doc)') or "accepted")
    print("  ", gate.offer('doc = "<script>new WebSocket(\\"ws://evil\\")</script>"'))

    demo.section("3. In the browser")
    server.llm.delay = 0.03
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_selector("text=generating...", timeout=15000)
            print("  while streaming:", page.inner_text(".openui-view").replace("\n", " | "))
            demo.screenshot(page, server.HERE / "demo_streaming.png")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            inner = page.frame_locator("iframe.genui-sandbox")
            inner.locator("#min").evaluate("el => { el.value = 20; el.dispatchEvent(new Event('input')); }")
            inner.locator("#ebike").check()
            inner.locator("#book").click()
            inner.locator("#msg").filter(has_text="Booked").wait_for(timeout=15000)
            print("  frame after the new prices statement:", inner.locator("#msg").inner_text())
            demo.screenshot(page, server.HERE / "demo.png")
            page.click(".tabs button:has-text('raw')")
            print("  raw tab shows the source:", page.inner_text(".artifact pre")[:60].replace("\n", " "), "...")
    srv.shutdown()


if __name__ == "__main__":
    main()
