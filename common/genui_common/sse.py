"""Server-Sent Events: one frame per message, frames end with a blank line.

    event: optional-name
    data: {"json": "payload"}

AG-UI, our A2UI stream and the harness web surface all ride on this framing.
"""

from __future__ import annotations

import json


def frame(data, event: str | None = None) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, separators=(",", ":"))
    head = f"event: {event}\n" if event else ""
    return head + "".join(f"data: {line}\n" for line in payload.split("\n")) + "\n"


def parse(stream_text: str) -> list[tuple[str | None, object]]:
    """Split a recorded SSE body into (event, data) pairs; data is JSON-decoded when possible."""
    out = []
    for block in stream_text.replace("\r\n", "\n").split("\n\n"):
        if not block.strip():
            continue
        event, data = None, []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
        raw = "\n".join(data)
        try:
            out.append((event, json.loads(raw)))
        except ValueError:
            out.append((event, raw))
    return out
