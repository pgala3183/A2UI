"""Run the MCP Apps declarative codelab: a spec as structuredContent, a generic view.

    python demo.py      (scripted models; add GENUI_LIVE=1 to use Claude on both sides)
"""

import json

import server  # first: sets sys.path
import mcp_app
from genui_common import demo
from mcp_http import McpHttpClient


def main():
    srv, url = mcp_app.start(server.app)
    demo.section("1. tools/list and one tools/call")
    client = McpHttpClient(url + "/mcp")
    client.initialize()
    for t in client.request("tools/list")["tools"]:
        print(f"  {t['name']:<18} _meta={json.dumps(t.get('_meta'))}")
    result = client.request("tools/call", {"name": "render_dashboard", "arguments": {"question": "network?"}})
    spec = result["structuredContent"]["spec"]
    print(f"  content (for the host's model): {result['content'][0]['text']!r}")
    print(f"  structuredContent.spec: root={spec['root']}, {len(spec['elements'])} elements, "
          f"types={sorted({e['type'] for e in spec['elements'].values()})}")

    demo.section("2. In the host: the view draws the spec, a button calls an app-only tool")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_function("document.body.dataset.connected === '1'", timeout=20000)
            page.click("#run")
            view = page.frame_locator("iframe.genui-sandbox")
            view.locator("h3").wait_for(timeout=20000)
            print("  view:", view.locator("h3").inner_text(), "| rows:", view.locator("table tr").count() - 1)
            view.locator("button:has-text('Only stations needing attention')").click()
            view.locator("h3:has-text('needing attention')").wait_for(timeout=15000)
            print("  after the button:", view.locator("h3").inner_text(), "| rows:", view.locator("table tr").count() - 1)
            print("  model context recorded by the host:", page.evaluate("JSON.stringify(window.host.modelContext.at(-1).content)"))
            demo.screenshot(page, server.HERE / "demo.png")
    mcp_app.stop(srv)


if __name__ == "__main__":
    main()
