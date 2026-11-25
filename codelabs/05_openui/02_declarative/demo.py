"""Run the OpenUI declarative codelab: streaming, forward references, token counts.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import server  # first: sets sys.path
from genui_common import demo, tokens
from openui_parse import Program, resolve


def flat(tree, elements):
    """The same UI as a json-render element map, for a fair size comparison."""
    props = {}
    children = []
    for key, value in tree["props"].items():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "type" in value[0]:
            children = [flat(child, elements) for child in value]
        else:
            props[key] = value
    elements[tree["id"]] = {"type": tree["type"], "props": props, **({"children": children} if children else {})}
    return tree["id"]


def main():
    srv, url = server.app.start()
    demo.section("1. The program, as it streams")
    frames = demo.post_sse(f"{url}/run", {"prompt": "dashboard"})
    program = Program()
    for event, data in frames:
        if event == "line":
            program.add(data["line"])
            missing = [n["id"] for n in _missing(resolve(program, server.LIBRARY))]
            print(f"  {data['line'][:64]:<66} missing now: {', '.join(missing) or '-'}")

    demo.section("2. Size next to an element-map JSON spec of the same UI")
    source = program.source()
    elements = {}
    root = flat(resolve(program, server.LIBRARY), elements)
    as_json = json.dumps({"root": root, "elements": elements})
    print(f"  OpenUI Lang       {len(source):>5} chars {tokens.count(source):>5} tokens")
    print(f"  json-render spec  {len(as_json):>5} chars {tokens.count(as_json):>5} tokens  ({tokens.method()})")

    demo.section("3. An action: only changed statements come back")
    for event, data in demo.post_sse(f"{url}/action", {"action": "filter_attention"}):
        if event == "line":
            print("  " + data["line"][:100])

    demo.section("4. In the browser")
    server.llm.delay = 0.04
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_selector(".w-skeleton", timeout=15000)
            demo.screenshot(page, server.HERE / "demo_streaming.png")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            page.click("button:has-text('Only stations needing attention')")
            page.wait_for_function("document.body.dataset.actions === '1'", timeout=30000)
            print("  after the action:", page.inner_text(".openui-view .w-card-title"), "| table rows:",
                  page.locator(".openui-view tbody tr").count())
            demo.screenshot(page, server.HERE / "demo.png")
    srv.shutdown()


def _missing(node):
    if isinstance(node, dict):
        if node.get("type") == "__missing":
            yield node
        for value in node.get("props", {}).values():
            yield from _missing(value)
    elif isinstance(node, list):
        for item in node:
            yield from _missing(item)


if __name__ == "__main__":
    main()
