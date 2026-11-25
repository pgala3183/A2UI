"""json-render's central idea: one catalog is the prompt, the validator and the registry.

json-render (https://github.com/vercel-labs/json-render) describes UI as a
flat spec and lets you declare, once, which components and actions exist:

    {"root": "dash",
     "elements": {"dash": {"type": "Card", "props": {"title": "..."}, "children": ["m1"]},
                  "m1":   {"type": "Metric", "props": {"label": "Bikes", "value": {"$state": "/bikes"}}}},
     "state": {"bikes": 49}}

* props may bind to state with {"$state": "/json/pointer"};
* elements may handle events: "on": {"press": {"action": "name", "params": {...}}};
* the built-in action setState changes state locally, without a round trip.

The library defines catalogs with Zod in TypeScript and renders with React.
This module is the same contract in Python with JSON Schema: ``prompt()``
for the model, ``check()`` for the server. The browser registry
(``registry.mjs``) is the third use of the same names.
"""

from __future__ import annotations

from jsonschema import Draft202012Validator

STATE_REF = {"type": "object", "properties": {"$state": {"type": "string", "pattern": "^/"}},
             "required": ["$state"], "additionalProperties": False}


def dyn(schema: dict) -> dict:
    """A prop that is either a literal or a {"$state": "/path"} binding."""
    return {"anyOf": [schema, STATE_REF]}


class Catalog:
    def __init__(self, components: dict, actions: dict):
        """components: name -> {"description", "props": {...JSON Schema...}, "required": [...], "children": bool}
        actions:    name -> {"description", "params": {...JSON Schema...}}"""
        self.components = components
        self.actions = {"setState": {"description": "Built in: set statePath to value, in the browser.",
                                     "params": {"statePath": {"type": "string"}, "value": {}}}, **actions}
        self._props = {name: Draft202012Validator({"type": "object", "properties": c["props"],
                                                   "required": c.get("required", []), "additionalProperties": False})
                       for name, c in components.items()}

    def prompt(self) -> str:
        lines = ["Components (props; '?' = optional; bind any prop to state with {\"$state\": \"/path\"}):"]
        for name, c in self.components.items():
            sig = ", ".join(f"{p}{'' if p in c.get('required', []) else '?'}" for p in c["props"])
            lines.append(f"- {name}({sig}){' + children' if c.get('children') else ''}: {c['description']}")
        lines.append("Actions (use in \"on\": {\"press\": {\"action\": name, \"params\": {...}}}):")
        for name, a in self.actions.items():
            lines.append(f"- {name}({', '.join(a['params'])}): {a['description']}")
        return "\n".join(lines)

    def check_element(self, element_id: str, element) -> list[str]:
        where = f"/elements/{element_id}"
        if not isinstance(element, dict) or element.get("type") not in self.components:
            kind = element.get("type") if isinstance(element, dict) else element
            return [f"{where}/type: unknown component {kind!r}; the catalog has {', '.join(self.components)}"]
        errors = [f"{where}/props/{'/'.join(map(str, e.path))}: {e.message}"
                  for e in self._props[element["type"]].iter_errors(element.get("props", {}))]
        children = element.get("children", [])
        if children and not self.components[element["type"]].get("children"):
            errors.append(f"{where}/children: {element['type']} takes no children")
        for event, handler in (element.get("on") or {}).items():
            if not isinstance(handler, dict) or handler.get("action") not in self.actions:
                errors.append(f"{where}/on/{event}: unknown action {handler!r}; allowed: {', '.join(self.actions)}")
        extra = set(element) - {"type", "props", "children", "on", "visible"}
        if extra:
            errors.append(f"{where}: unexpected keys {sorted(extra)}")
        return errors

    def check(self, spec) -> list[str]:
        if not isinstance(spec, dict) or not isinstance(spec.get("elements"), dict):
            return ["spec must be {root, elements, state?}"]
        errors = [] if spec.get("root") in spec["elements"] else [f"/root: {spec.get('root')!r} is not an element"]
        for element_id, element in spec["elements"].items():
            errors += self.check_element(element_id, element)
            for child in element.get("children", []) if isinstance(element, dict) else []:
                if child not in spec["elements"]:
                    errors.append(f"/elements/{element_id}/children: unknown element {child!r}")
        return errors
