"""Run the AG-UI mixed codelab: three runs, one confirmation, bikes moved.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import agent
import server
from genui_common import demo


def main():
    srv, url = server.app.start()
    demo.section("In the browser: build, act inside the frame, confirm, see state update")
    with demo.browser() as page:
        if not page:
            print("  (browser unavailable; run test_step.py for the wire-level checks)")
            return
        page.goto(url)
        page.click("#run")
        page.wait_for_function("document.body.dataset.runsDone === '1'", timeout=30000)
        print("  run 1 events:", page.eval_on_selector_all(".wire-item b", "els => [...new Set(els.map(e => e.textContent))].join(', ')"))
        print("  alert (render tool):", page.inner_text(".tool-area .w-alert"))
        print("  metric:", page.inner_text("[data-key=m_attention]").replace("\n", " "))
        inner = page.frame_locator("iframe.genui-sandbox")
        inner.locator("#bars .bar").first.wait_for(timeout=10000)
        inner.locator("#n").fill("8")
        inner.locator("#from").select_option("ferry")
        inner.locator("#to").select_option("mission")
        inner.locator("#apply").click()
        page.wait_for_selector("[data-confirm]", timeout=30000)
        print("  run 2 ended with a frontend tool call:", page.inner_text("[data-confirm]").replace("\n", " | "))
        demo.screenshot(page, agent.HERE / "demo_confirm.png")
        page.click("[data-confirm] button:has-text('Confirm')")
        page.wait_for_function("document.body.dataset.runsDone === '3'", timeout=30000)
        print("  run 3 reply:", page.locator(".bubble.assistant").last.inner_text().strip())
        print("  metric now:", page.inner_text("[data-key=m_attention]").replace("\n", " "))
        print("  frame kept running; it shows:", inner.locator("#bars").inner_text().replace("\n", " ")[:120])
        demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
