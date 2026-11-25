# Video script · Part 3 · MCP Apps (about 20 min)

## 0:00 What MCP Apps is (2 min)

**Screen:** `codelabs/03_mcp_apps/README.md`.
**Say:** "MCP Apps lets an MCP server ship UI to any host that supports it. Three additions: a ui:// resource with the mcp-app MIME type, a tool whose _meta.ui.resourceUri points at it, and a result with content for the model and structuredContent for the view. The host mounts the view in a sandboxed iframe and talks JSON-RPC over postMessage."
**Say:** "Each codelab is a real FastMCP server. The demo host in the same process only talks to it over MCP. Every server also runs over stdio for Claude Desktop."

## 2:00 Chapter 1 · Static: a pre-built view (5 min)

**Run:** `cd codelabs/03_mcp_apps/01_static`, `python demo.py`: initialize, tools/list with _meta, resources/read with the MIME type, tools/call.
**Run:** `python server.py`, http://127.0.0.1:8301, Run. Click Refresh, Ask the assistant why, Open station page. Point at each bridge message in the wire panel.
**Code:** `server.py` tool + resource → `_shared/mcp_app.py` `VIEW_META` → `view.html` `connect`, tool-result, `callServerTool` → `_shared/host/host.mjs` `ui/message` and `ui/open-link` handling, `cspFor`.
**Test:** `test_official_mcp_client_sees_the_same_thing`.
**Takeaway:** "Two pieces of metadata turn a tool into an app. The host decides what the app may do."

## 7:00 Chapter 2 · Declarative: a generic view (4 min)

**Run:** `02_declarative`, http://127.0.0.1:8302, Run, then "Only stations needing attention".
**Code:** `server.py` `generate_spec()` (the server's own model, validated) → `dashboard_action` with `visibility: ["app"]` → `view.html` `renderSpec` + `updateModelContext` → host `visibleTo`.
**Takeaway:** "One fixed view renders any validated spec; the model key stays on the server."

## 11:00 Chapter 3 · Open-ended: a nested sandbox (4 min)

**Run:** `03_open_ended`, http://127.0.0.1:8303, Run. In DevTools show two iframes, both `sandbox="allow-scripts"`. Book a ride; point at the app's message appearing in the host chat.
**Code:** why the resource is a fixed shell (README) → `server.py` `generate_html()` policy → `structuredContent` → `view.html` `mountGenerated` and the action whitelist → `book_ride` server price.
**Takeaway:** "Generated HTML rides in the tool result, two sandboxes deep."

## 15:00 Chapter 4 · Mixed: catalog + generated region (4 min)

**Run:** `04_mixed`, http://127.0.0.1:8304, Run. Apply a plan in the simulator; point at the catalog half updating and the simulator keeping its selection. Click "Ask the assistant for a plan"; point at the answer using the app's context.
**Code:** `server.py` spec with one GeneratedView and the three-part structuredContent → `view.html` per-region slots → `rebalance` (app-only, capacity) → host folding `ui/update-model-context` into the next turn.
**Takeaway:** "Catalog and generated UI in one app, inside a host you do not control."

## 19:00 Wrap-up (1 min)

Show the `claude_desktop_config.json` snippet from the theme README. `python run_all.py codelabs/03_mcp_apps`. "Ship the same UI into your own product with AG-UI, and into other people's hosts with MCP Apps."
