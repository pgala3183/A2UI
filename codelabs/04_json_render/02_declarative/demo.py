"""Run the json-render declarative codelab: the patch stream and first paint.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import agent
import server
from genui_common import demo


def main():
    srv, url = server.app.start()
    demo.section("1. The patch stream")
    frames = demo.post_sse(f"{url}/run", {"prompt": "dashboard"})
    patches = [d for e, d in frames if e == "patch"]
    for i, op in enumerate(patches, 1):
        value = json.dumps(op["value"])
        print(f"  {i:>2}. {op['op']} {op['path']:<18} {value[:70]}{'...' if len(value) > 70 else ''}")
    first = next(i for i, op in enumerate(patches, 1) if op["path"].startswith("/elements/"))
    total = sum(len(json.dumps(op)) for op in patches)
    upto = sum(len(json.dumps(op)) for op in patches[:first])
    print(f"  first paint needs patches 1-{first} ({upto} of {total} chars, {100 * upto // total}% of the stream)")

    demo.section("2. Refresh: state patches only")
    for event, data in demo.post_sse(f"{url}/action", {"action": "refresh", "params": {}}):
        print(f"  {event}: {data['op']} {data['path']} {json.dumps(data['value'])[:60]}")

    demo.section("3. In the browser (slowed down so first paint is visible)")
    server.llm.delay = 0.02 if hasattr(server.llm, "delay") else None
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("window.jr.timing.firstPaint !== null", timeout=30000)
            demo.screenshot(page, agent.HERE / "demo_first_paint.png")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            t = page.evaluate("window.jr.timing")
            print(f"  first paint {t['firstPaint']} ms, complete {t['done']} ms, {t['patches']} patches")
            before = page.inner_text("[data-key=m2]").replace("\n", " ")
            page.click("button:has-text('Refresh')")
            page.wait_for_function("document.body.dataset.actions === '1'", timeout=15000)
            print(f"  {before} -> {page.inner_text('[data-key=m2]').replace(chr(10), ' ')} (a /state patch, no element resent)")
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
