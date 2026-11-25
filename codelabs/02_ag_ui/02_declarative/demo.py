"""Run the AG-UI declarative codelab: state snapshot, deltas, and a smaller second run.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import agent
import server
from genui_common import demo, jsonpatch


def summarize(events, state=None):
    state = state or {}
    for event in events:
        if event["type"] == "STATE_SNAPSHOT":
            state = event["snapshot"]
            print(f"  STATE_SNAPSHOT  {json.dumps(event['snapshot'])}")
        elif event["type"] == "STATE_DELTA":
            state = jsonpatch.apply_patch(state, event["delta"])
            for op in event["delta"]:
                value = json.dumps(op.get("value", ""))
                print(f"  STATE_DELTA     {op['op']:<7} {op['path']:<36} {value[:46]}")
        elif event["type"] in ("STEP_STARTED", "STEP_FINISHED", "RUN_FINISHED"):
            print(f"  {event['type']:<15} {event.get('stepName', event.get('result', ''))}")
    return state


def main():
    srv, url = server.app.start()
    demo.section("1. First run: the UI is built in state, one element per delta")
    body = {"threadId": "t", "runId": "r1", "state": {}, "messages": [{"id": "1", "role": "user", "content": "Build me a dashboard"}]}
    events = [e for _, e in demo.post_sse(f"{url}/agent", body)]
    state = summarize(events)
    first_bytes = sum(len(json.dumps(e)) for e in events if e["type"].startswith("STATE"))

    demo.section("2. Second run: a button click sends the state back; only changes are patched")
    body = {"threadId": "t", "runId": "r2", "state": state, "messages": [
        {"id": "1", "role": "user", "content": "Build me a dashboard"},
        {"id": "2", "role": "user", "content": '[ui action] filter_attention {}'}]}
    events = [e for _, e in demo.post_sse(f"{url}/agent", body)]
    summarize(events, state)
    second_bytes = sum(len(json.dumps(e)) for e in events if e["type"].startswith("STATE"))
    print(f"  state bytes on the wire: first run {first_bytes}, second run {second_bytes}")

    demo.section("3. In the browser")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            print("  title:", page.inner_text("[data-key=dash] .w-card-title"), "| table rows:",
                  page.locator("[data-key=table] tbody tr").count())
            page.click("button:has-text('Only stations needing attention')")
            page.wait_for_function("document.body.dataset.actions === '1'", timeout=30000)
            print("  after the click:", page.inner_text("[data-key=dash] .w-card-title"), "| table rows:",
                  page.locator("[data-key=table] tbody tr").count())
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
