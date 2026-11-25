"""A tiny synchronous MCP client over Streamable HTTP, for tests and demos.

It speaks the same JSON-RPC the host page's ``mcp-client.mjs`` speaks:
``initialize`` (the server answers with an ``mcp-session-id`` header),
``notifications/initialized``, then ``tools/list``, ``tools/call`` and
``resources/read``. The servers run with ``json_response=True``, so every
answer is a plain JSON body.
"""

from __future__ import annotations

import json
import urllib.request

PROTOCOL = "2025-06-18"


class McpHttpClient:
    def __init__(self, url: str):
        self.url = url
        self.session = None
        self.next_id = 0
        self.log: list[tuple[str, str]] = []

    def _post(self, body: dict):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "mcp-protocol-version": PROTOCOL}
        if self.session:
            headers["mcp-session-id"] = self.session
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            self.session = response.headers.get("mcp-session-id") or self.session
            raw = response.read().decode()
        return json.loads(raw) if raw.strip() else None

    def request(self, method: str, params: dict | None = None):
        self.next_id += 1
        self.log.append(("->", method))
        reply = self._post({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}})
        if "error" in reply:
            raise RuntimeError(reply["error"])
        self.log.append(("<-", method))
        return reply["result"]

    def notify(self, method: str, params: dict | None = None):
        self._post({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL,
            "capabilities": {"extensions": {"io.modelcontextprotocol/ui": {"mimeTypes": ["text/html;profile=mcp-app"]}}},
            "clientInfo": {"name": "genux-test-host", "version": "1.0"}})
        self.notify("notifications/initialized")
        return result
