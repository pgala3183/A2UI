"""A second renderer for the same spec: plain text for a terminal.

json-render's pitch is "one catalog, many renderers" (React, React Native,
a terminal through Ink...). This renderer walks the same element map the
browser draws and resolves the same {"$state": ...} bindings. The one part a
terminal cannot run, the HtmlArtifact, degrades to a one-line pointer. That
fallback is the price of the open-ended region in a mixed UI.
"""

from __future__ import annotations

from genui_common import jsonpatch


def resolve(value, state):
    if isinstance(value, dict):
        if "$state" in value:
            return jsonpatch.get(state, value["$state"])
        if "$not" in value:
            return not resolve(value["$not"], state)
        return {k: resolve(v, state) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, state) for v in value]
    return value


def render_text(spec: dict, width: int = 72) -> str:
    state = spec.get("state", {})
    lines: list[str] = []

    def walk(element_id: str, depth: int):
        element = spec["elements"].get(element_id)
        pad = "  " * depth
        if element is None:
            lines.append(f"{pad}[missing {element_id}]")
            return
        if "visible" in element and not resolve(element["visible"], state):
            lines.append(f"{pad}({element['type']} {element_id} hidden)")
            return
        p = resolve(element.get("props", {}), state)
        kind = element["type"]
        if kind == "Card":
            lines.append(f"{pad}+-- {p.get('title', '')} " + "-" * max(4, width - len(pad) - len(p.get("title", "")) - 6))
        elif kind == "Metric":
            lines.append(f"{pad}{p['label']}: {p['value']}")
        elif kind == "Text":
            lines.append(f"{pad}{p['text']}")
        elif kind == "Button":
            handler = element.get("on", {}).get("press", {})
            lines.append(f"{pad}[ {p['label']} ]  -> {handler.get('action', '')}")
        elif kind == "Table":
            cols = p["columns"]
            rows = [[str(c) for c in r] for r in p["rows"]]
            widths = [max(len(str(c)), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
            lines.append(pad + "  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
            lines.extend(pad + "  ".join(c.ljust(w) for c, w in zip(r, widths)) for r in rows)
        elif kind == "BarChart":
            top = max([1, *p["values"]])
            for label, value in zip(p["labels"], p["values"]):
                lines.append(f"{pad}{str(label)[:18]:<18} {'#' * round(30 * value / top)} {value}")
        elif kind == "HtmlArtifact":
            size = len("".join(p.get("chunks", [])))
            lines.append(f"{pad}[interactive: {p.get('title', element_id)} - {size} chars of HTML; open the web view to use it]")
        elif kind not in ("Row", "Column"):
            lines.append(f"{pad}[{kind}]")
        for child in element.get("children", []):
            walk(child, depth + (1 if kind in ("Card", "Column", "Row") else 0))

    if spec.get("root"):
        walk(spec["root"], 0)
    return "\n".join(lines)
