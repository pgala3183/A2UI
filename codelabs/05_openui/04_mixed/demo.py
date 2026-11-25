"""Run the OpenUI mixed codelab: where the tokens go, and updates by statement.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import server  # first: sets sys.path
from genui_common import demo, tokens


def main():
    srv, url = server.app.start()
    demo.section("1. Where the tokens go")
    lines = [d["line"] for e, d in demo.post_sse(f"{url}/run", {"prompt": "desk"}) if e == "line"]
    artifact = sum(tokens.count(line) for line in lines if line.startswith("simDoc"))
    total = sum(tokens.count(line) for line in lines)
    print(f"  {len(lines)} statements, {total} tokens ({tokens.method()})")
    print(f"  the simulator document alone: {artifact} tokens ({100 * artifact // total}%)")
    print(f"  the other {len(lines) - 1} statements: {total - artifact} tokens")

    demo.section("2. An action answered with statements")
    server.network = server.bikes.Network()
    for event, data in demo.post_sse(f"{url}/action", {"action": "rebalance", "source": "sim",
                                                       "params": {"from": "ferry", "to": "mission", "count": 6}}):
        print("  " + data["line"][:100])

    demo.section("3. In the browser")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.wait_for_selector("#run")
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            sim = page.frame_locator("iframe.genui-sandbox")
            sim.locator("#bars .bar").first.wait_for(timeout=10000)
            sim.locator("#n").fill("6")
            sim.locator("#from").select_option("ferry")
            sim.locator("#to").select_option("mission")
            sim.locator("#apply").click()
            page.wait_for_function("document.body.dataset.actions === '1'", timeout=15000)
            print("  catalog part:", page.inner_text(".openui-view .w-card").replace("\n", " | "))
            print("  note:", page.inner_text(".openui-view .w-markdown"), "| simulator kept its selection:",
                  sim.locator("#from").input_value())
            demo.screenshot(page, server.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
