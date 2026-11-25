"""Run the A2UI open-ended codelab: HTML in an HtmlFrame, data in, actions out.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import agent
import server
from genui_common import demo, tokens
from genui_common.sandbox import check_html


def main():
    srv, url = server.app.start()
    demo.section("1. What the model sent")
    for event, data in demo.post_sse(f"{url}/run", {"prompt": "Give me an interactive trip-cost calculator"}):
        if isinstance(data, dict) and "updateComponents" in data:
            frame = data["updateComponents"]["components"][0]
            html = frame["html"]
            print(f"  updateComponents: 1 component, {frame['component']} with {len(html)} chars of HTML "
                  f"({tokens.count(html)} tokens, {tokens.method()})")
            print(f"  content policy violations: {check_html(html) or 'none'}")
        else:
            demo.show(data, 150)

    demo.section("2. The policy rejects what a sandbox should never see")
    bad = '<html><body><script src="https://cdn.example.com/x.js"></script><script>fetch("/steal")</script></body></html>'
    print("  ", check_html(bad))

    demo.section("3. In the browser: server price change, then a booking from inside the iframe")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            inner = page.frame_locator("iframe.genui-sandbox")
            inner.locator("#msg").filter(has_text="Peak").wait_for(timeout=10000)
            print("  frame after updateDataModel:", inner.locator("#rule").inner_text(), "|", inner.locator("#msg").inner_text())
            inner.locator("#min").evaluate("el => { el.value = 40; el.dispatchEvent(new Event('input')); }")
            inner.locator("#ebike").check()
            print("  frame shows:", inner.locator("#cost").inner_text(), "for 40 min on an e-bike")
            inner.locator("#book").click()
            inner.locator("#msg").filter(has_text="Booked").wait_for(timeout=10000)
            print("  server answer, shown inside the frame:", inner.locator("#msg").inner_text())
            sandbox = page.get_attribute("iframe.genui-sandbox", "sandbox")
            print(f"  iframe sandbox attribute: {sandbox!r} (no allow-same-origin)")
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
