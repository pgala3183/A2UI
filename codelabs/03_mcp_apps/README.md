# Theme 03 · MCP Apps: UI inside a host you do not control

[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) (the MCP extension from SEP-1865) lets an ordinary MCP server ship a user interface to any host that supports it (Claude, ChatGPT, VS Code, Goose...). Three additions to a normal server:

1. a **resource** with a `ui://` URI and MIME type `text/html;profile=mcp-app`: a complete HTML document, the *view*;
2. a **tool** whose `_meta.ui.resourceUri` points at that resource;
3. a **tool result** with `content` (text, for the model and for hosts without UI) and `structuredContent` (data, for the view).

The host reads the resource, mounts it in a sandboxed iframe and talks to it with JSON-RPC over `postMessage`:

| direction | messages used in these codelabs |
|---|---|
| view → host | `ui/initialize`, `ui/notifications/initialized`, `ui/notifications/size-changed`, `tools/call`, `ui/message`, `ui/open-link`, `ui/update-model-context` |
| host → view | `ui/notifications/tool-input`, `ui/notifications/tool-result` |

Each codelab runs a real FastMCP server (`mcp` Python SDK, 1.x) over Streamable HTTP, plus a small **demo host** page in the same process. Host and server still only talk over MCP. Every server also runs over stdio for a real host: `python server.py --stdio`.

## The four modes in MCP Apps

| Codelab | Mode | The `ui://` view | New idea |
|---|---|---|---|
| [01_static](01_static/README.md) | static | a hand-written dashboard | the bridge, `tools/call` from a view, `ui/message`, `ui/open-link` |
| [02_declarative](02_declarative/README.md) | declarative | a generic catalog renderer | the server's own model writes the spec; app-only tools via `_meta.ui.visibility` |
| [03_open_ended](03_open_ended/README.md) | open-ended | a fixed shell | generated HTML in `structuredContent`, mounted in a nested sandbox |
| [04_mixed](04_mixed/README.md) | mixed | catalog + generated region | two halves in one view; `ui/update-model-context` |

## Shared code (`_shared/`)

| File | Role |
|---|---|
| `mcp_app.py` | `MIME`, `VIEW_META` (CSP lists), `load_view()` (inlines the view kit), `http_app()` (MCP at `/mcp` + host page + host model at `/host/chat`) |
| `view-kit.js` | inlined into every view: the app side of the bridge, a few widgets, `renderSpec()`, `mountGenerated()` |
| `host/host.mjs` | the demo host: MCP client, sandboxed mount with a CSP from `_meta.ui.csp`, the JSON-RPC bridge, tool visibility |
| `host/mcp-client.mjs`, `mcp_http.py` | MCP over Streamable HTTP for the browser and for tests |

`_shared/host/host.mjs`:

```js
const visibleTo = (tool, who) => Boolean(tool) && (tool._meta?.ui?.visibility ?? ['model', 'app']).includes(who);
```

The host decides what a view may do: here it hides app-only tools from the model and model-only tools from views, shows links instead of navigating, and proxies `tools/call` only to the server that owns the view.

## Use a server in a real host

Each server speaks MCP over stdio. For Claude Desktop, add it to `claude_desktop_config.json` (use your own absolute path):

```json
{
  "mcpServers": {
    "bikes-static": {
      "command": "python",
      "args": ["C:/path/to/A2UI/codelabs/03_mcp_apps/01_static/server.py", "--stdio"]
    }
  }
}
```

A host that supports MCP Apps renders the view; a host that does not shows the text `content`. Hosts differ in which bridge methods they implement, so check your host's documentation. The recorded demos use the demo host in this repository.

## Run the theme

```bash
python run_all.py codelabs/03_mcp_apps
cd codelabs/03_mcp_apps/01_static && python demo.py
cd codelabs/03_mcp_apps/01_static && python server.py     # http://127.0.0.1:8301 (MCP at /mcp)
```

Ports: 8301 (static), 8302 (declarative), 8303 (open-ended), 8304 (mixed).
