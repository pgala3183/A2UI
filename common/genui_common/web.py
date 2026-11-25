"""A tiny HTTP server on the standard library: routes, static files and SSE.

Every codelab (except the MCP Apps ones, which use the MCP SDK's server) runs
on this. A route handler receives a ``Request`` and returns one of:

* a ``dict`` or ``list``        -> sent as JSON
* a ``Response``                -> sent as is
* a generator                   -> streamed as Server-Sent Events; each item is
                                   a dict (one ``data:`` frame), an
                                   ``(event_name, dict)`` pair, or a raw frame str

Static mounts map URL prefixes to directories. ``/common/`` always serves the
shared browser modules in ``common/web``; ``/`` serves the codelab's page.
"""

from __future__ import annotations

import json
import mimetypes
import os
import threading
import types
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import sse

COMMON_WEB = Path(__file__).resolve().parent.parent / "web"
TYPES = {".mjs": "text/javascript", ".js": "text/javascript", ".css": "text/css", ".html": "text/html",
         ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".txt": "text/plain"}


@dataclass
class Request:
    method: str
    path: str
    query: dict
    headers: dict
    body: bytes = b""

    @property
    def json(self):
        return json.loads(self.body or b"{}")


@dataclass
class Response:
    body: str | bytes
    content_type: str = "text/plain; charset=utf-8"
    status: int = 200
    headers: dict = field(default_factory=dict)


class App:
    def __init__(self, page_dir: Path | str, mounts: dict[str, Path | str] | None = None, title: str = "genui"):
        self.title = title
        self.routes: dict[tuple[str, str], callable] = {}
        self.mounts = {"/common/": COMMON_WEB, **{k: Path(v) for k, v in (mounts or {}).items()}}
        self.mounts["/"] = Path(page_dir)
        self.log: list[str] = []  # request lines, handy in tests and demos

    def route(self, method: str, path: str):
        """Register a handler. A path ending in "*" matches every path with that prefix."""
        def register(fn):
            self.routes[(method.upper(), path)] = fn
            return fn
        return register

    def get(self, path):
        return self.route("GET", path)

    def post(self, path):
        return self.route("POST", path)

    # -- serving ---------------------------------------------------------
    def handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"  # one response per connection: SSE ends when the stream ends

            def log_message(self, fmt, *args):
                if os.environ.get("GENUI_HTTP_LOG"):
                    super().log_message(fmt, *args)

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

            def _dispatch(self, method):
                url = urlparse(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                request = Request(method, url.path, parse_qs(url.query), dict(self.headers), body)
                app.log.append(f"{method} {url.path}")
                handler = app.routes.get((method, url.path))
                if handler is None:  # prefix routes: register a path ending in "*"
                    handler = next((fn for (m, path), fn in app.routes.items()
                                    if m == method and path.endswith("*") and url.path.startswith(path[:-1])), None)
                try:
                    if handler is not None:
                        self._send(handler(request))
                    elif method == "GET":
                        self._static(url.path)
                    else:
                        self._send(Response("not found", status=404))
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass  # the browser went away mid-stream; nothing to do
                except Exception as error:  # report, do not kill the server
                    try:
                        self._send(Response(json.dumps({"error": str(error)}), "application/json", 500))
                    except Exception:
                        pass

            def _send(self, result):
                if isinstance(result, types.GeneratorType):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    for item in result:
                        if isinstance(item, str):
                            chunk = item
                        elif isinstance(item, tuple):
                            chunk = sse.frame(item[1], event=item[0])
                        else:
                            chunk = sse.frame(item)
                        self.wfile.write(chunk.encode("utf-8"))
                        self.wfile.flush()
                    return
                if not isinstance(result, Response):
                    result = Response(json.dumps(result), "application/json")
                body = result.body.encode("utf-8") if isinstance(result.body, str) else result.body
                self.send_response(result.status)
                self.send_header("Content-Type", result.content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for key, value in result.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def _static(self, path):
                for prefix in sorted(app.mounts, key=len, reverse=True):
                    if not path.startswith(prefix):
                        continue
                    root = app.mounts[prefix].resolve()
                    rel = path[len(prefix):] or "index.html"
                    target = (root / rel).resolve()
                    if root not in target.parents and target != root:
                        break  # path escapes the mount: refuse
                    if target.is_dir():
                        target = target / "index.html"
                    if target.is_file():
                        kind = TYPES.get(target.suffix) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                        if kind.startswith("text/") or kind == "application/json":
                            kind += "; charset=utf-8"
                        self._send(Response(target.read_bytes(), kind))
                        return
                    break
                self._send(Response("not found", status=404))

        return Handler

    def serve(self, port: int = 8000, host: str = "127.0.0.1") -> ThreadingHTTPServer:
        server = ThreadingHTTPServer((host, port), self.handler())
        server.daemon_threads = True
        return server

    def start(self, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
        """Serve in a background thread (tests and demos). Returns (server, base_url)."""
        server = self.serve(port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_address[1]}"

    def run(self, port: int = 8000):
        """Serve in the foreground until Ctrl+C."""
        server = self.serve(port)
        print(f"{self.title} on http://127.0.0.1:{port}  (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


def port_from_argv(default: int) -> int:
    import sys

    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            return int(arg.split("=", 1)[1])
    return int(os.environ.get("PORT", default))
