"""Run the json-render static codelab: one catalog, three uses.

    python demo.py      (scripted model; add GENUI_LIVE=1 to use Claude)
"""

import agent
import server
from genui_common import demo


def main():
    demo.section("1. Use 1 - the catalog as the prompt")
    demo.wrap(agent.CATALOG.prompt())

    demo.section("2. Use 2 - the catalog as the validator")
    srv, url = server.app.start()
    for event, data in demo.post_sse(f"{url}/run", {"prompt": "How is Market St doing?"}):
        if event == "patch":
            element = data["value"]["elements"]["w"]
            print(f"  patch replace '' -> one {element['type']} with props {sorted(element['props'])}")
        else:
            demo.show({event: data}, 200)

    demo.section("3. Use 3 - the catalog as the registry (browser)")
    with demo.browser() as page:
        if page:
            page.goto(url)
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '1'", timeout=30000)
            print("  rendered:", page.inner_text("[data-key=w]").replace("\n", " | ")[:100])
            page.fill(".prompt-input", "How much is a 30 minute ride?")
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '2'", timeout=30000)
            print("  second prompt rendered:", page.inner_text("[data-key=w]").replace("\n", " | "))
            page.fill(".prompt-input", "How is Market St doing?")
            page.click("#run")
            page.wait_for_function("document.body.dataset.runs === '3'", timeout=30000)
            demo.screenshot(page, agent.HERE / "demo.png")
    srv.shutdown()


if __name__ == "__main__":
    main()
