"""Run the json-render mixed codelab: browser + terminal renderers of one spec.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import urllib.request

import agent
import server
from genui_common import demo


def main():
    srv, url = server.app.start()
    with demo.browser() as page:
        if not page:
            demo.post_sse(f"{url}/run", {"prompt": "desk"})
        else:
            demo.section("1. In the browser: setState (local) and rebalance (server)")
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            print("  table visible before toggle:", page.is_visible("[data-key=table]"))
            requests_before = len(server.app.log)
            page.click("button:has-text('Show / hide station table')")
            print("  table visible after toggle:", page.is_visible("[data-key=table]"),
                  f"| requests caused by setState: {len(server.app.log) - requests_before}")
            sim = page.frame_locator("iframe.genui-sandbox")
            sim.locator("#bars .bar").first.wait_for(timeout=10000)
            sim.locator("#n").fill("6")
            sim.locator("#from").select_option("ferry")
            sim.locator("#to").select_option("mission")
            sim.locator("#apply").click()
            page.wait_for_function("document.body.dataset.actions === '1'", timeout=15000)
            print("  patches from the action:", page.eval_on_selector_all(".wire-item b", "els => els.slice(-4).map(e => e.textContent).join(', ')"))
            print("  catalog metric:", page.inner_text("[data-key=m2]").replace("\n", ": "), "| frame:", sim.locator("#msg").inner_text())
            demo.screenshot(page, agent.HERE / "demo.png")

    demo.section("2. The same spec in the terminal renderer (GET /text)")
    print(urllib.request.urlopen(f"{url}/text").read().decode())
    srv.shutdown()


if __name__ == "__main__":
    main()
