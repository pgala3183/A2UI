"""Run the MCP Apps static codelab: MCP on the wire, then the host page.

    python demo.py      (scripted host model; add GENUI_LIVE=1 to use Claude as the host's model)
"""

import json

import server  # first: sets sys.path
import mcp_app
from genui_common import demo
from mcp_http import McpHttpClient


def main():
    srv, url = mcp_app.start(server.app)
    demo.section("1. What any MCP host sees")
    client = McpHttpClient(url + "/mcp")
    init = client.initialize()
    print(f"  initialize -> server {init['serverInfo']['name']}, protocol {init['protocolVersion']}, session {client.session[:8]}...")
    tool = client.request("tools/list")["tools"][0]
    print(f"  tools/list -> {tool['name']}  _meta: {json.dumps(tool['_meta'])}")
    resource = client.request("resources/read", {"uri": server.VIEW_URI})["contents"][0]
    print(f"  resources/read -> {resource['mimeType']}, {len(resource['text'])} chars, _meta: {json.dumps(resource['_meta'])}")
    result = client.request("tools/call", {"name": "station_dashboard", "arguments": {"station_id": "market"}})
    print(f"  tools/call -> content: {result['content'][0]['text']!r}")
    print(f"               structuredContent keys: {sorted(result['structuredContent'])}")

    demo.section("2. The demo host: model -> tool call -> view -> bridge")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_function("document.body.dataset.connected === '1'", timeout=20000)
            page.click("#run")
            view = page.frame_locator("iframe.genui-sandbox")
            view.locator("h3").wait_for(timeout=20000)
            print("  view title:", view.locator("h3").inner_text())
            view.locator("button:has-text('Refresh')").click()
            page.wait_for_function("[...document.querySelectorAll('.wire-item b')].filter(b => b.textContent === 'mcp tools/call').length >= 2", timeout=15000)
            view.locator("button:has-text('Ask the assistant why')").click()
            page.wait_for_function("document.body.dataset.turns === '2'", timeout=15000)
            view.locator("button:has-text('Open station page')").click()
            page.wait_for_timeout(500)
            print("  chat:")
            for bubble in page.query_selector_all(".bubble"):
                print("   ", bubble.inner_text()[:110])
            print("  bridge traffic:", ", ".join(dict.fromkeys(
                page.eval_on_selector_all(".wire-item b", "els => els.map(e => e.textContent)"))))
            demo.screenshot(page, server.HERE / "demo.png")
    mcp_app.stop(srv)


if __name__ == "__main__":
    main()
