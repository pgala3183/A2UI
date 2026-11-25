"""MCP Apps plumbing shared by the four MCP Apps codelabs.

MCP Apps (the MCP extension from SEP-1865, https://modelcontextprotocol.io/extensions/apps/overview)
adds UI to an ordinary MCP server with three things:

1. a resource whose URI starts with ``ui://`` and whose MIME type is
   ``text/html;profile=mcp-app``: a complete HTML document, the *view*;
2. a tool whose ``_meta.ui.resourceUri`` points at that resource;
3. a tool result with ``content`` (text, for the model and for hosts without
   UI) and ``structuredContent`` (data, for the view).

The host reads the resource, mounts it in a sandboxed iframe, and talks to it
with JSON-RPC over postMessage (``ui/initialize``, ``ui/notifications/tool-result``,
``tools/call``, ``ui/message`` ...). This module serves one FastMCP server at
``/mcp`` plus a small demo host page at ``/`` from the same process. The host
and the server still only talk to each other over MCP.
"""

from __future__ import annotations

import mimetypes
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "common")]

from genui_common.llm import get_llm  # noqa: E402
from genui_common.web import COMMON_WEB  # noqa: E402

MIME = "text/html;profile=mcp-app"
# Restrictive by default: the view may not connect anywhere or load anything external.
VIEW_META = {"ui": {"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": True}}
VIEW_KIT = HERE / "view-kit.js"

mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/javascript", ".js")

HOST_SYSTEM = ("You are the assistant inside an MCP host. Use the available tools to answer. "
               "Tools with a user interface render themselves; after calling one, say one short sentence.")


def load_view(path: Path) -> str:
    """Read a view and inline the view kit (bridge + widgets): what a bundler would do.

    Views run in an opaque-origin iframe with ``default-src 'none'``, so they
    cannot load scripts from anywhere. Everything they need is inlined.
    """
    html = path.read_text(encoding="utf-8")
    return html.replace("<!--VIEW_KIT-->", "<script>\n" + VIEW_KIT.read_text(encoding="utf-8") + "\n</script>")


def http_app(mcp, step_dir: Path, host_respond, config: dict):
    """The MCP endpoint (/mcp), the demo host page (/), and the host's model (/host/chat)."""
    from starlette.concurrency import run_in_threadpool
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route
    from starlette.staticfiles import StaticFiles

    app = mcp.streamable_http_app()
    host_llm = {"llm": get_llm(host_respond)}

    async def chat(request):
        body = await request.json()
        tools = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t["inputSchema"]}
                 for t in body.get("tools", [])]

        def complete():
            return [e for e in host_llm["llm"].stream(HOST_SYSTEM, body["messages"], tools)][-1]

        done = await run_in_threadpool(complete)
        return JSONResponse({"content": done["content"]})

    async def host_config(request):
        return JSONResponse(config)

    app.router.routes.extend([
        Route("/host/chat", chat, methods=["POST"]),
        Route("/host/config", host_config),
        Mount("/common", StaticFiles(directory=COMMON_WEB)),
        Mount("/shared", StaticFiles(directory=HERE)),
        Mount("/", StaticFiles(directory=HERE / "host", html=True)),
    ])
    app.state.host_llm = host_llm
    return app


def start(app, port: int = 0):
    """Run uvicorn in a background thread (tests and demos). Returns (server, base_url)."""
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    bound = server.servers[0].sockets[0].getsockname()[1]
    return server, f"http://127.0.0.1:{bound}"


def stop(server):
    server.should_exit = True


def run(app, port: int, title: str):
    import uvicorn

    print(f"{title}: host page http://127.0.0.1:{port}/  MCP endpoint http://127.0.0.1:{port}/mcp", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
