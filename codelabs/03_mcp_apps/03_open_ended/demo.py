"""Run the MCP Apps open-ended codelab: a shell view, a nested sandbox, a booking.

    python demo.py      (scripted models; add GENUI_LIVE=1 to use Claude on both sides)
"""

import server  # first: sets sys.path
import mcp_app
from genui_common import demo, tokens
from mcp_http import McpHttpClient


def main():
    srv, url = mcp_app.start(server.app)
    demo.section("1. The fixed shell and the generated widget")
    client = McpHttpClient(url + "/mcp")
    client.initialize()
    shell = client.request("resources/read", {"uri": server.VIEW_URI})["contents"][0]["text"]
    result = client.request("tools/call", {"name": "generate_widget", "arguments": {"request": "trip calculator"}})
    html = result["structuredContent"]["html"]
    print(f"  ui:// shell: {len(shell)} chars (fetched once, cacheable)")
    print(f"  generated widget: {len(html)} chars, {tokens.count(html)} tokens ({tokens.method()}) in structuredContent")
    print(f"  content for the host's model: {result['content'][0]['text']!r}")

    demo.section("2. In the host: two sandboxes deep, a booking, a message back to the chat")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_function("document.body.dataset.connected === '1'", timeout=20000)
            page.click("#run")
            view = page.frame_locator("iframe.genui-sandbox")
            widget = view.frame_locator("iframe.k-generated")
            widget.locator("#cost").wait_for(timeout=20000)
            widget.locator("#min").evaluate("el => { el.value = 30; el.dispatchEvent(new Event('input')); }")
            widget.locator("#ebike").check()
            print("  widget shows:", widget.locator("#cost").inner_text())
            widget.locator("#book").click()
            widget.locator("#msg").filter(has_text="Booked").wait_for(timeout=15000)
            print("  widget message:", widget.locator("#msg").inner_text())
            page.wait_for_function("document.body.dataset.turns === '2'", timeout=15000)
            print("  host chat:", " | ".join(b.inner_text()[:70] for b in page.query_selector_all(".bubble")[-2:]))
            print("  sandbox attributes:", page.get_attribute("iframe.genui-sandbox", "sandbox"), "/",
                  view.locator("iframe.k-generated").get_attribute("sandbox"))
            demo.screenshot(page, server.HERE / "demo.png")
    mcp_app.stop(srv)


if __name__ == "__main__":
    main()
