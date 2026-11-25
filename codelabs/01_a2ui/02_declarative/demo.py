"""Run the A2UI declarative codelab: prompt, correction loop, form, action.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import agent
import server
from genui_common import demo, tokens


def main():
    demo.section("1. The catalog becomes the system prompt")
    print(f"  system prompt: {len(agent.SYSTEM)} chars, {tokens.count(agent.SYSTEM)} tokens ({tokens.method()})")
    demo.wrap("\n".join(agent.SYSTEM.splitlines()[-9:]))

    srv, url = server.app.start()
    demo.section("2. The stream: validate each line, correct, retry")
    for event, data in demo.post_sse(f"{url}/run", {"prompt": "I found a broken bike, help me report it"}):
        if event in ("note", "error"):
            demo.show({event: data}, 200)
        else:
            kind = next(k for k in data if k != "version")
            body = data[kind]
            detail = f"{len(body['components'])} components" if kind == "updateComponents" else body.get("path", "")
            print(f"  {kind:<17} {detail}")

    demo.section("3. The form in a browser: type, check, click")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            try:
                page.wait_for_function("document.querySelector('[data-key=title]') && document.querySelector('.w-skeleton')", timeout=8000)
                demo.screenshot(page, agent.HERE / "demo_streaming.png")
                print("  (mid-stream: ids that have not arrived yet render as skeletons)")
            except Exception:
                print("  (stream finished before a mid-stream screenshot could be taken)")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            page.fill("[data-key=bike_field] input", "B-2231")
            page.fill("[data-key=issue_field] textarea", "Rear brake does not grip")
            page.check("[data-key=urgent_box] input")
            print("  data model after typing:", page.evaluate("JSON.stringify([...a2ui.processor.surfaces.values()][0].data)"))
            page.click("[data-key=send] button, button:has-text('Send report')")
            page.wait_for_function("document.querySelector('[data-key=result]')?.textContent.includes('Ticket')", timeout=15000)
            print("  server answer:", page.inner_text("[data-key=result]"))
            print("  button label now:", page.inner_text("[data-key=send]"))
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
