"""The element-map catalog shared by AG-UI state (theme 02) and the harness (theme 06).

A spec is a flat map, the shape that streams well:

    {"root": "dash", "elements": {"dash": {"type": "Card", "props": {...}, "children": ["a", "b"]}, ...}}

``validate_spec`` checks the shape, every element against its type's JSON
Schema, that children exist, and that there are no cycles. Errors are short
strings with a path, written to be handed back to a model.
"""

from __future__ import annotations

from jsonschema import Draft202012Validator

S = {"type": "string"}
N = {"type": ["number", "string"]}
GAP = {"enum": ["small", "medium", "large"]}

# type -> (description, props schema, required props, may have children)
CATALOG = {
    "Card": ("A bordered section with an optional title.", {"title": S, "subtitle": S}, [], True),
    "Row": ("Children side by side.", {"gap": GAP}, [], True),
    "Column": ("Children stacked vertically.", {"gap": GAP}, [], True),
    "Text": ("A line of text.", {"text": S, "variant": {"enum": ["h1", "h2", "h3", "body", "caption"]}}, ["text"], False),
    "Metric": ("A labelled number with an optional delta like '+8%'.", {"label": S, "value": N, "delta": S}, ["label", "value"], False),
    "Table": ("Rows of cells under column headers.",
              {"columns": {"type": "array", "items": S}, "rows": {"type": "array", "items": {"type": "array"}}}, ["columns", "rows"], False),
    "BarChart": ("A bar chart.", {"title": S, "labels": {"type": "array", "items": S},
                                  "values": {"type": "array", "items": {"type": "number"}}}, ["labels", "values"], False),
    "Alert": ("A status message.", {"level": {"enum": ["info", "success", "warning", "critical"]}, "text": S}, ["text"], False),
    "Badge": ("A small label.", {"text": S, "tone": {"enum": ["neutral", "good", "warn", "bad"]}}, ["text"], False),
    "Divider": ("A horizontal rule.", {}, [], False),
    "Button": ("A button that sends a named action to the server.",
               {"label": S, "action": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}, "params": {"type": "object"},
                "variant": {"enum": ["primary", "secondary", "danger"]}}, ["label", "action"], False),
}

GENERATED_VIEW = ("A sandboxed region whose HTML arrives separately (by artifact id).",
                  {"artifact": {"type": "string"}, "height": {"type": "number"}}, ["artifact"], False)


def _validator(props: dict, required: list[str], children: bool) -> Draft202012Validator:
    schema = {"type": "object", "properties": {
        "type": S, "props": {"type": "object", "properties": props, "required": required, "additionalProperties": False},
        "children": {"type": "array", "items": S, **({} if children else {"maxItems": 0})},
        "visible": {"type": "boolean"}}, "required": ["type"], "additionalProperties": False}
    return Draft202012Validator(schema)


class Catalog:
    def __init__(self, types: dict):
        self.types = types
        self._validators = {name: _validator(p, r, c) for name, (_, p, r, c) in types.items()}

    def with_types(self, **extra) -> "Catalog":
        return Catalog({**self.types, **extra})

    def check_element(self, element_id: str, element) -> list[str]:
        if not isinstance(element, dict):
            return [f"/elements/{element_id}: must be an object"]
        kind = element.get("type")
        if kind not in self.types:
            return [f"/elements/{element_id}/type: unknown type {kind!r}; allowed: {', '.join(self.types)}"]
        return [f"/elements/{element_id}/{'/'.join(map(str, e.path))}: {e.message}"
                for e in self._validators[kind].iter_errors(element)]

    def check_spec(self, spec) -> list[str]:
        if not isinstance(spec, dict) or not isinstance(spec.get("elements"), dict):
            return ["spec must be {root, elements: {...}}"]
        elements = spec["elements"]
        errors = []
        if spec.get("root") not in elements:
            errors.append(f"/root: {spec.get('root')!r} is not an element")
        for element_id, element in elements.items():
            errors += self.check_element(element_id, element)
            for child in (element.get("children") or []) if isinstance(element, dict) else []:
                if child not in elements:
                    errors.append(f"/elements/{element_id}/children: unknown child {child!r}")
        # cycles: walk from the root
        seen, stack = set(), [(spec.get("root"), ())]
        while stack:
            node, path = stack.pop()
            if node in path:
                errors.append(f"/elements/{node}: cycle")
                continue
            if node in seen or node not in elements:
                continue
            seen.add(node)
            stack += [(c, path + (node,)) for c in elements[node].get("children") or []]
        return errors

    def prompt(self) -> str:
        lines = ["Element types (props; '?' = optional):"]
        for name, (description, props, required, children) in self.types.items():
            sig = ", ".join(f"{p}{'' if p in required else '?'}" for p in props)
            lines.append(f"- {name}({sig}){' + children' if children else ''}: {description}")
        return "\n".join(lines)


CATALOG_V1 = Catalog(CATALOG)
