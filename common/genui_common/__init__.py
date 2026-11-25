"""Shared plumbing for every GenUX codelab.

Nothing in here is specific to one protocol. Each codelab imports these
helpers and keeps its own protocol code (A2UI, AG-UI, MCP Apps, json-render,
OpenUI Lang, harness) in its own directory, so the code you read in a
codelab is the code that teaches its idea.

    llm.py        the model: ScriptedLLM (offline, default) or ClaudeLLM (GENUI_LIVE=1)
    web.py        a tiny standard-library HTTP server with JSON, static files and SSE
    sse.py        Server-Sent Events framing and parsing
    jsonpatch.py  RFC 6901 JSON Pointer and RFC 6902 JSON Patch (add/replace/remove)
    sandbox.py    CSP injection and a content policy for model-written HTML
    bikes.py      the shared demo domain: a bike-share network and two HTML widgets
    tokens.py     token counting with tiktoken (falls back to an estimate)
    demo.py       helpers for demo.py scripts: start a server, drive a headless browser
"""
