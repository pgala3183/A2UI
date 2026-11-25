"""Run the A2UI mixed codelab: catalog + HtmlFrame, two kinds of action.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import agent
import server
from genui_common import demo, tokens


def main():
    srv, url = server.app.start()
    demo.section("1. What the model wrote: mostly catalog, one HtmlFrame")
    catalog_chars = frame_chars = 0
    for event, data in demo.post_sse(f"{url}/run", {"prompt": "Build me a rebalancing desk"}):
        if isinstance(data, dict) and "updateComponents" in data:
            for c in data["updateComponents"]["components"]:
                size = len(json.dumps(c))
                if c["component"] == "HtmlFrame":
                    frame_chars += size
                else:
                    catalog_chars += size
            names = [c["component"] for c in data["updateComponents"]["components"]]
            print(f"  updateComponents: {', '.join(names)}")
        elif isinstance(data, dict):
            kind = next(k for k in data if k != "version")
            print(f"  {kind}: {data[kind].get('path', data[kind].get('catalogId', ''))}")
    total = catalog_chars + frame_chars
    print(f"  catalog components: {catalog_chars} chars; HtmlFrame: {frame_chars} chars "
          f"({100 * frame_chars // total}% of the layout for one interactive region)")
    print(f"  tokens: layout {tokens.count(json.dumps(agent.respond('', [])))} total ({tokens.method()})")

    demo.section("2. In the browser: an action from inside the frame, then one from a catalog button")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            inner = page.frame_locator("iframe.genui-sandbox")
            inner.locator("#bars .bar").first.wait_for(timeout=10000)
            print("  before:", page.inner_text("[data-key=attention]"))
            inner.locator("#n").fill("8")
            inner.locator("#from").select_option("ferry")
            inner.locator("#to").select_option("mission")
            inner.locator("#apply").click()
            page.wait_for_function("document.querySelector('[data-key=message]')?.textContent.startsWith('Moved')", timeout=10000)
            print("  catalog Text after the frame's action:", page.inner_text("[data-key=message]"))
            print("  catalog Text now:", page.inner_text("[data-key=attention]"))
            print("  frame kept its selection:", inner.locator("#from").input_value(), "->", inner.locator("#to").input_value())
            demo.screenshot(page, agent.HERE / "demo.png")
            page.click("[data-key=refresh] button, button:has-text('Refresh numbers')")
            page.wait_for_function("document.querySelector('[data-key=message]')?.textContent.startsWith('Numbers refreshed')", timeout=10000)
            print("  after the catalog button:", page.inner_text("[data-key=message]"))
            print("  wire:", page.eval_on_selector_all(".wire-item b", "els => els.slice(-8).map(e => e.textContent).join(', ')"))
    srv.shutdown()


if __name__ == "__main__":
    main()
