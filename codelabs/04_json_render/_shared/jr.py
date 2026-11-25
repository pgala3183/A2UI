"""json-render on the server: catalogs, the patch stream, and a patch gate.

The model streams RFC 6902 operations, one per line (json-render's
"SpecStream"). ``PatchGate`` applies each one to a server-side mirror of the
spec and keeps it only if the result still validates against the catalog,
so the browser never receives an element the catalog does not allow.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

from catalog import Catalog, dyn  # noqa: E402,F401
from genui_common import jsonpatch  # noqa: E402

S, N = {"type": "string"}, {"type": ["number", "string"]}

PRIMITIVES = {
    "Card": {"description": "A section with a title.", "props": {"title": dyn(S), "subtitle": dyn(S)}, "children": True},
    "Row": {"description": "Children side by side.", "props": {"gap": {"enum": ["small", "medium", "large"]}}, "children": True},
    "Column": {"description": "Children stacked.", "props": {"gap": {"enum": ["small", "medium", "large"]}}, "children": True},
    "Text": {"description": "Text.", "props": {"text": dyn(N), "variant": {"enum": ["h1", "h2", "h3", "body", "caption"]}}, "required": ["text"]},
    "Metric": {"description": "A labelled number.", "props": {"label": dyn(S), "value": dyn(N), "delta": dyn(S)}, "required": ["label", "value"]},
    "Table": {"description": "A table.", "props": {"columns": dyn({"type": "array"}), "rows": dyn({"type": "array"})}, "required": ["columns", "rows"]},
    "BarChart": {"description": "A bar chart.", "props": {"title": S, "labels": dyn({"type": "array"}), "values": dyn({"type": "array"})},
                 "required": ["labels", "values"]},
    "Badge": {"description": "A small label.", "props": {"text": dyn(S), "tone": {"enum": ["neutral", "good", "warn", "bad"]}}, "required": ["text"]},
    "Button": {"description": "A button; handle on.press.", "props": {"label": S, "variant": {"enum": ["primary", "secondary"]}}, "required": ["label"]},
}

HTML_ARTIFACT = {
    "description": "An interactive HTML document (inline CSS/JS, no network). Stream it as props.chunks, "
                   "appending with op add and path .../props/chunks/-, then set props.complete to true.",
    "props": {"title": S, "chunks": {"type": "array", "items": S}, "complete": {"type": "boolean"},
              "height": {"type": "number"}},
    "required": ["chunks"],
}


def patch_lines(chunks):
    """Text chunks -> one parsed operation per complete line (fences and blanks skipped)."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip() and not line.strip().startswith("```"):
                yield line.strip()
    if buffer.strip() and not buffer.strip().startswith("```"):
        yield buffer.strip()


class PatchGate:
    """Apply operations to a mirror spec; refuse any that break the catalog."""

    def __init__(self, catalog: Catalog, spec: dict | None = None, extra_check=None):
        self.catalog = catalog
        self.spec = spec or {"root": None, "elements": {}, "state": {}}
        self.extra_check = extra_check  # fn(element_id, element) -> list[str], e.g. an HTML policy

    def offer(self, op) -> list[str]:
        if not isinstance(op, dict) or op.get("op") not in ("add", "replace", "remove"):
            return [f"not an add/replace/remove operation: {str(op)[:80]}"]
        path = op.get("path", "")
        if not (path == "/root" or path.startswith("/elements/") or path.startswith("/state")):
            return [f"{path}: operations may touch /root, /elements/... or /state/... only"]
        try:
            candidate = jsonpatch.apply_patch(self.spec, [op])
        except jsonpatch.PatchError as error:
            return [f"{path}: {error}"]
        errors = []
        if path.startswith("/elements/"):
            element_id = jsonpatch.parse_pointer(path)[1]
            element = candidate["elements"].get(element_id)
            if element is not None:
                errors = self.catalog.check_element(element_id, element)
                if not errors and self.extra_check:
                    errors = self.extra_check(element_id, element)
        if not errors:
            self.spec = candidate
        return errors


def sse_patch(op: dict) -> tuple[str, dict]:
    return ("patch", op)


def dumps(op: dict) -> str:
    return json.dumps(op, separators=(",", ":"))
