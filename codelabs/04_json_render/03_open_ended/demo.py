"""Run the json-render open-ended codelab: chunked HTML, a gate, a booking.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import agent
import server
from genui_common import demo


def main():
    srv, url = server.app.start()
    demo.section("1. The stream: a document in chunks")
    patches = [d for e, d in demo.post_sse(f"{url}/run", {"prompt": "calculator"}) if e == "patch"]
    chunks = [p for p in patches if p["path"].endswith("/chunks/-")]
    for p in patches[:3] + [{"op": "...", "path": f"({len(chunks) - 1} more chunk patches)", "value": ""}] + patches[-2:]:
        print(f"  {p['op']:<7} {p['path']:<36} {json.dumps(p['value'])[:56]}")
    print(f"  {len(chunks)} chunks, {sum(len(c['value']) for c in chunks)} characters of HTML")

    demo.section("2. The gate: a document that fails the policy never completes")
    bad = server.PatchGate(agent.CATALOG, extra_check=agent.html_policy)
    for op in [{"op": "add", "path": "/root", "value": "x"},
               {"op": "add", "path": "/elements/x", "value": {"type": "HtmlArtifact", "props": {"chunks": ["<script>fetch('/a')</script>"]}}},
               {"op": "add", "path": "/elements/x/props/complete", "value": True}]:
        print(f"  {op['path']:<28} -> {bad.offer(op) or 'accepted'}")

    demo.section("3. In the browser")
    server.llm.delay = 0.03
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_selector("text=generating...", timeout=20000)
            demo.screenshot(page, agent.HERE / "demo_streaming.png")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            inner = page.frame_locator("iframe.genui-sandbox")
            inner.locator("#min").evaluate("el => { el.value = 45; el.dispatchEvent(new Event('input')); }")
            inner.locator("#book").click()
            inner.locator("#msg").filter(has_text="Booked").wait_for(timeout=15000)
            print("  frame message (from a /state patch):", inner.locator("#msg").inner_text())
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
