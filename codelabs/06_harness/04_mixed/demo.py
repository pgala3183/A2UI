"""Run the harness mixed codelab: build, act in the simulator, approve, refresh.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import os

os.environ.setdefault("GENUI_TERMINAL_MIRROR", "0")

import agent  # noqa: E402
import server  # noqa: E402
from genui_common import demo  # noqa: E402
from harness.terminal import TerminalSurface  # noqa: E402
from rich.console import Console  # noqa: E402


def main():
    demo.section("1. Terminal surface: build the desk, then a simulator action, approved")
    surface = TerminalSurface(Console(width=100, color_system=None))
    h = agent.make_harness()
    for event in h.ask("Build me a rebalancing desk"):
        if not (event["type"] == "ui" and event["kind"] == "html"):
            surface.handle(event)
        else:
            print(f"  [ui html: {event['title']}, embedded in a GeneratedView; actions {event['actions']}]")
    request = None
    for event in h.ui_action("sim", "rebalance", {"from": "ferry", "to": "mission", "count": 6}):
        surface.handle(event)
        request = event if event["type"] == "permission_request" else request
    for event in h.resume(request["id"], True):
        surface.handle(event)

    demo.section("2. Web surface")
    srv, url = server.app.start()
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_function("document.body.dataset.streams === '1'", timeout=30000)
            sim = page.frame_locator("iframe.genui-sandbox")
            sim.locator("#bars .bar").first.wait_for(timeout=10000)
            print("  desk:", page.inner_text("[data-view=desk] .w-row").replace("\n", " "), "| alert:", page.inner_text("[data-view=alert]"))
            sim.locator("#n").fill("6")
            sim.locator("#from").select_option("ferry")
            sim.locator("#to").select_option("mission")
            sim.locator("#apply").click()
            page.wait_for_selector("[data-permission]", timeout=15000)
            demo.screenshot(page, agent.HERE / "demo_permission.png")
            page.click("[data-permission] button:has-text('Approve')")
            page.wait_for_function("document.body.dataset.streams === '3'", timeout=30000)
            print("  after approval:", page.inner_text("[data-view=desk] .w-row").replace("\n", " "),
                  "| simulator:", sim.locator("#msg").inner_text(), "| selection kept:", sim.locator("#from").input_value())
            demo.screenshot(page, agent.HERE / "demo.png")
            page.click("button:has-text('Refresh numbers')")
            page.wait_for_function("document.body.dataset.streams === '4'", timeout=30000)
            print("  refresh (a declared spec action):", sim.locator("#msg").inner_text())
    srv.shutdown()


if __name__ == "__main__":
    main()
