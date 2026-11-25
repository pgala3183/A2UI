"""Run the harness declarative codelab: a failed render, a fix, two surfaces.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import os

os.environ.setdefault("GENUI_TERMINAL_MIRROR", "0")

import agent  # noqa: E402
import server  # noqa: E402
from genui_common import demo  # noqa: E402
from harness.terminal import run_cli  # noqa: E402
from rich.console import Console  # noqa: E402


def main():
    demo.section("1. Terminal surface: python cli.py \"Make me a rebalancing report\"")
    run_cli(agent.make_harness, ["Make me a rebalancing report"], console=Console(width=100, color_system=None))

    demo.section("2. Web surface")
    srv, url = server.app.start()
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_function("document.body.dataset.streams === '1'", timeout=30000)
            print("  transcript:")
            for bubble in page.query_selector_all(".bubble")[1:]:
                print("   ", bubble.inner_text()[:105])
            print("  rendered:", page.inner_text("[data-view=report] .w-card-title"))
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
