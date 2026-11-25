"""Run the OpenUI static codelab: one statement, and what it costs next to JSON.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import json

import server  # first: sets sys.path
from genui_common import demo, tokens
from openui_parse import Program, resolve


def main():
    demo.section("1. The prompt the library generates")
    demo.wrap(server.openui.prompt(server.LIBRARY))

    srv, url = server.app.start()
    demo.section("2. The answer: one line")
    frames = demo.post_sse(f"{url}/run", {"prompt": "How is Market St doing?"})
    line = next(d["line"] for e, d in frames if e == "line")
    print("  " + line)
    program = Program()
    program.add(line)
    tree = resolve(program, server.LIBRARY)
    print("  resolved props:", json.dumps(tree["props"])[:110], "...")

    demo.section("3. The same widget in other formats")
    as_tool_call = json.dumps({"name": "show_station_card", "input": tree["props"]})
    as_json_render = json.dumps({"root": "w", "elements": {"w": {"type": "StationCard", "props": tree["props"]}}})
    for label, text in (("OpenUI Lang", line), ("tool call (AG-UI static)", as_tool_call), ("json-render spec", as_json_render)):
        print(f"  {label:<26} {len(text):>4} chars {tokens.count(text):>4} tokens")
    print(f"  ({tokens.method()})")

    demo.section("4. In the browser")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            print("  rendered:", page.inner_text(".openui-view").replace("\n", " | ")[:90])
            demo.screenshot(page, server.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
