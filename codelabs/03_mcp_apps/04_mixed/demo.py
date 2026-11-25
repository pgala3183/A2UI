"""Run the MCP Apps mixed codelab: catalog + generated region, an app-only tool.

    python demo.py      (scripted models; add GENUI_LIVE=1 to use Claude on both sides)
"""

import json

import server  # first: sets sys.path
import mcp_app
from genui_common import demo
from mcp_http import McpHttpClient


def main():
    srv, url = mcp_app.start(server.app)
    demo.section("1. One tool result, three parts")
    client = McpHttpClient(url + "/mcp")
    client.initialize()
    data = client.request("tools/call", {"name": "ops_desk", "arguments": {}})["structuredContent"]
    spec_chars, html_chars = len(json.dumps(data["spec"])), len(json.dumps(data["generated"]))
    print(f"  spec: {len(data['spec']['elements'])} catalog elements, {spec_chars} chars")
    print(f"  generated: {list(data['generated'])}, {html_chars} chars")
    print(f"  stations: {[s['id'] for s in data['stations']]}")
    server.network = server.bikes.Network()  # reset before the browser run

    demo.section("2. In the host: act inside the nested frame, then ask the host's model")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_function("document.body.dataset.connected === '1'", timeout=20000)
            page.click("#run")
            view = page.frame_locator("iframe.genui-sandbox")
            sim = view.frame_locator("iframe.k-generated")
            sim.locator("#bars .bar").first.wait_for(timeout=20000)
            print("  catalog half:", view.locator("[data-slot=header]").inner_text().replace("\n", " | "))
            sim.locator("#n").fill("6")
            sim.locator("#from").select_option("ferry")
            sim.locator("#to").select_option("mission")
            sim.locator("#apply").click()
            view.locator("body[data-moves='1']").wait_for(timeout=15000)
            print("  after the frame's action:", view.locator("[data-slot=header]").inner_text().replace("\n", " | "))
            print("  simulator message:", sim.locator("#msg").inner_text(), "| selection kept:", sim.locator("#from").input_value())
            view.locator("button:has-text('Ask the assistant for a plan')").click()
            page.wait_for_function("document.body.dataset.turns === '2'", timeout=15000)
            print("  host model, with the app's context:", page.locator(".bubble.assistant").last.inner_text()[:110])
            demo.screenshot(page, server.HERE / "demo.png")
    mcp_app.stop(srv)


if __name__ == "__main__":
    main()
