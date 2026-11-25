"""Run the harness open-ended codelab: permission, artifact, a declared action.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import os
import urllib.request

os.environ.setdefault("GENUI_TERMINAL_MIRROR", "0")

import agent  # noqa: E402
import server  # noqa: E402
from genui_common import demo  # noqa: E402
from harness.terminal import run_cli  # noqa: E402
from rich.console import Console  # noqa: E402


def main():
    console = Console(width=100, color_system=None)
    demo.section('1. Terminal: python cli.py "Make me an interactive trip-cost calculator" --no')
    run_cli(agent.make_harness, ["Make me an interactive trip-cost calculator", "--no"], console=console)
    demo.section('2. Terminal: the same with --yes')
    run_cli(agent.make_harness, ["Make me an interactive trip-cost calculator", "--yes"], console=console)

    demo.section("3. Web surface: approve, use the artifact, a declared and an undeclared action")
    srv, url = server.app.start()
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_selector("[data-permission]", timeout=30000)
            print("  paused:", page.inner_text("[data-permission]").replace("\n", " | ")[:120])
            demo.screenshot(page, agent.HERE / "demo_permission.png")
            page.click("[data-permission] button:has-text('Approve')")
            page.wait_for_function("document.body.dataset.streams === '2'", timeout=30000)
            inner = page.frame_locator("iframe.genui-sandbox")
            inner.locator("#min").evaluate("el => { el.value = 40; el.dispatchEvent(new Event('input')); }")
            inner.locator("#book").click()
            inner.locator("#msg").filter(has_text="Booked").wait_for(timeout=15000)
            print("  frame after send_to_view:", inner.locator("#msg").inner_text())
            demo.screenshot(page, agent.HERE / "demo.png")
            response = urllib.request.urlopen(f"{url}/artifacts/calc.html")
            print("  GET /artifacts/calc.html CSP header:", response.headers["Content-Security-Policy"][:60], "...")
            undeclared = demo.post_sse(f"{url}/ui-action", {"view": "calc", "action": "delete_account", "params": {}})
            print("  undeclared action:", undeclared[0][1])
    srv.shutdown()


if __name__ == "__main__":
    main()
