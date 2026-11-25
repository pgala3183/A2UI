"""Run the harness static codelab on both surfaces.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import os

os.environ.setdefault("GENUI_TERMINAL_MIRROR", "0")  # keep the demo output to one terminal rendering

import agent  # noqa: E402
import server  # noqa: E402
from genui_common import demo  # noqa: E402
from harness.terminal import run_cli  # noqa: E402
from rich.console import Console  # noqa: E402


def main():
    demo.section("1. Terminal surface: python cli.py \"Which stations need rebalancing?\"")
    run_cli(agent.make_harness, ["Which stations need rebalancing?"], console=Console(width=100, color_system=None))

    demo.section("2. Web surface: the same events in the browser")
    srv, url = server.app.start()
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_function("document.body.dataset.streams === '1'", timeout=30000)
            print("  views on the page:", page.eval_on_selector_all("[data-view]", "els => els.map(e => e.dataset.view).join(', ')"))
            print("  final answer:", page.locator(".bubble.assistant").last.inner_text()[:100])
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
