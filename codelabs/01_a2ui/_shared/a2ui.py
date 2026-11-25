"""A2UI v0.9 on the server: the four envelopes, a catalog, and validation.

A2UI (Agent-to-User Interface, https://a2ui.org) sends UI as a stream of
JSON messages. Every server-to-client message is one of four envelopes:

    {"version": "v0.9", "createSurface":    {"surfaceId", "catalogId"}}
    {"version": "v0.9", "updateComponents": {"surfaceId", "components": [...]}}
    {"version": "v0.9", "updateDataModel":  {"surfaceId", "path", "value"}}
    {"version": "v0.9", "deleteSurface":    {"surfaceId"}}

Components are a flat list joined by ids; one of them has id "root". Values
are either literals or data bindings ``{"path": "/json/pointer"}`` into the
surface's data model. Structure (components) and data (the data model)
travel in separate messages, so data can change without resending layout.

The client answers with one envelope, ``{"version": "v0.9", "action": {...}}``,
when the user triggers a component's action.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from jsonschema import Draft202012Validator

VERSION = "v0.9"
BASIC_CATALOG_ID = "https://a2ui.org/specification/v0_9/basic_catalog.json"
ENVELOPES = ("createSurface", "updateComponents", "updateDataModel", "deleteSurface")

ID = {"type": "string", "minLength": 1}
PATH = {"type": "object", "properties": {"path": {"type": "string", "pattern": "^/"}},
        "required": ["path"], "additionalProperties": False}
DYNAMIC_STRING = {"anyOf": [{"type": "string"}, {"type": "number"}, PATH]}
DYNAMIC_BOOL = {"anyOf": [{"type": "boolean"}, PATH]}
ACTION = {
    "type": "object",
    "properties": {"event": {"type": "object", "properties": {
        "name": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
        "context": {"type": "object"}}, "required": ["name"], "additionalProperties": False}},
    "required": ["event"], "additionalProperties": False,
}
CHILDREN = {"type": "array", "items": ID}
ALIGN = {"enum": ["start", "center", "end", "stretch", "spaceBetween"]}

# The part of the Basic Catalog these codelabs render. Each entry: a description
# for the prompt, the props as JSON Schema, and the required props.
BASIC = {
    "Text": ("Text, plain or markdown heading ('# Title').",
             {"text": DYNAMIC_STRING, "variant": {"enum": ["h1", "h2", "h3", "h4", "h5", "caption", "body"]}}, ["text"]),
    "Card": ("A bordered container with exactly one child.", {"child": ID}, ["child"]),
    "Column": ("Children stacked vertically.", {"children": CHILDREN, "justify": ALIGN, "align": ALIGN}, ["children"]),
    "Row": ("Children side by side.", {"children": CHILDREN, "justify": ALIGN, "align": ALIGN}, ["children"]),
    "Button": ("A button. 'child' is the id of a Text used as its label. 'action.event' is sent to the server.",
               {"child": ID, "variant": {"enum": ["primary", "borderless"]}, "action": ACTION}, ["child", "action"]),
    "TextField": ("A text input bound two-way to the data model through 'value': {'path': ...}.",
                  {"label": DYNAMIC_STRING, "value": DYNAMIC_STRING,
                   "variant": {"enum": ["shortText", "longText", "number", "obscured"]}}, ["label"]),
    "CheckBox": ("A checkbox bound two-way to a boolean in the data model.",
                 {"label": DYNAMIC_STRING, "value": DYNAMIC_BOOL}, ["label", "value"]),
    "Divider": ("A horizontal rule.", {"axis": {"enum": ["horizontal", "vertical"]}}, []),
}


class Catalog:
    """A named set of components. Validates components and describes itself to a model."""

    def __init__(self, catalog_id: str, components: dict, extra_checks=None):
        self.id = catalog_id
        self.components = components
        self.extra_checks = extra_checks or {}  # name -> fn(component) -> list[str]
        self._validators = {name: Draft202012Validator(self._schema(name)) for name in components}

    def _schema(self, name: str) -> dict:
        _, props, required = self.components[name]
        return {"type": "object",
                "properties": {"id": ID, "component": {"const": name}, "weight": {"type": "number"}, **props},
                "required": ["id", "component", *required], "additionalProperties": False}

    def check(self, component) -> list[str]:
        if not isinstance(component, dict):
            return ["component must be an object"]
        name = component.get("component")
        if name not in self.components:
            return [f"unknown component {name!r}; this catalog has {', '.join(self.components)}"]
        errors = [f"{'/'.join(map(str, e.path)) or name}: {e.message}" for e in self._validators[name].iter_errors(component)]
        errors += self.extra_checks.get(name, lambda c: [])(component)
        return errors

    def prompt(self) -> str:
        lines = [f"Catalog {self.id}. Components (common props: id, component, weight):"]
        for name, (description, props, required) in self.components.items():
            sig = ", ".join(f"{p}{'' if p in required else '?'}" for p in props)
            lines.append(f"- {name}({sig}): {description}")
        return "\n".join(lines)


BASIC_CATALOG = Catalog(BASIC_CATALOG_ID, BASIC)


# -- envelopes ----------------------------------------------------------------
def create_surface(surface_id: str, catalog_id: str = BASIC_CATALOG_ID) -> dict:
    return {"version": VERSION, "createSurface": {"surfaceId": surface_id, "catalogId": catalog_id}}


def update_components(surface_id: str, components: list[dict]) -> dict:
    return {"version": VERSION, "updateComponents": {"surfaceId": surface_id, "components": components}}


def update_data_model(surface_id: str, path: str, value) -> dict:
    return {"version": VERSION, "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value}}


def delete_surface(surface_id: str) -> dict:
    return {"version": VERSION, "deleteSurface": {"surfaceId": surface_id}}


def error(code: str, surface_id: str | None, path: str, message: str) -> dict:
    """The spec's error shape; sent to the model (and logged) when a message fails."""
    return {"version": VERSION, "error": {"code": code, "surfaceId": surface_id, "path": path, "message": message}}


def kind(message: dict) -> str | None:
    keys = [k for k in ENVELOPES if k in message]
    return keys[0] if len(keys) == 1 else None


class Mirror:
    """The server's view of the surfaces it created: which catalog each one uses.

    ``check`` validates one envelope against the surface's own catalog and
    returns a list of A2UI error objects (empty when the message is valid).
    """

    def __init__(self, catalogs: list[Catalog]):
        self.catalogs = {c.id: c for c in catalogs}
        self.surfaces: dict[str, Catalog] = {}

    def check(self, message) -> list[dict]:
        if not isinstance(message, dict) or message.get("version") != VERSION:
            return [error("VALIDATION_FAILED", None, "/version", f"version must be {VERSION}")["error"]]
        k = kind(message)
        if k is None:
            return [error("VALIDATION_FAILED", None, "/", f"exactly one of {', '.join(ENVELOPES)} is required")["error"]]
        body = message[k]
        sid = body.get("surfaceId")
        if not isinstance(sid, str):
            return [error("VALIDATION_FAILED", None, f"/{k}/surfaceId", "surfaceId is required")["error"]]
        if k == "createSurface":
            if sid in self.surfaces:
                return [error("VALIDATION_FAILED", sid, "/createSurface/surfaceId",
                              "surface already exists; send deleteSurface first")["error"]]
            if body.get("catalogId") not in self.catalogs:
                return [error("VALIDATION_FAILED", sid, "/createSurface/catalogId",
                              f"unknown catalog; use one of {list(self.catalogs)}")["error"]]
            return []
        if sid not in self.surfaces:
            return [error("VALIDATION_FAILED", sid, f"/{k}/surfaceId", "createSurface must come first")["error"]]
        if k == "updateComponents":
            problems = []
            for i, component in enumerate(body.get("components") or []):
                for text in self.surfaces[sid].check(component):
                    problems.append(error("VALIDATION_FAILED", sid, f"/updateComponents/components/{i}", text)["error"])
            if not body.get("components"):
                problems.append(error("VALIDATION_FAILED", sid, "/updateComponents/components", "empty list")["error"])
            return problems
        if k == "updateDataModel" and not str(body.get("path", "/")).startswith("/"):
            return [error("VALIDATION_FAILED", sid, "/updateDataModel/path", "path must be a JSON Pointer")["error"]]
        return []

    def apply(self, message: dict) -> list[dict]:
        """Validate, then record surface lifecycle. Returns the errors (if any)."""
        problems = self.check(message)
        if not problems:
            k = kind(message)
            body = message[k]
            if k == "createSurface":
                self.surfaces[body["surfaceId"]] = self.catalogs[body["catalogId"]]
            elif k == "deleteSurface":
                self.surfaces.pop(body["surfaceId"], None)
        return problems


# -- streaming ------------------------------------------------------------------
def jsonl(chunks):
    """Turn a stream of text chunks into complete lines (one A2UI message per line)."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line and not line.startswith("```"):
                yield line
    if buffer.strip() and not buffer.strip().startswith("```"):
        yield buffer.strip()


def parse_action(body: dict) -> dict:
    """Validate the client's action envelope and return its body."""
    if body.get("version") != VERSION or not isinstance(body.get("action"), dict):
        raise ValueError("expected {version: 'v0.9', action: {...}}")
    action = body["action"]
    for field in ("name", "surfaceId", "sourceComponentId"):
        if not isinstance(action.get(field), str):
            raise ValueError(f"action.{field} must be a string")
    if not isinstance(action.get("context", {}), dict):
        raise ValueError("action.context must be an object")
    return action


def now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def compact(message: dict) -> str:
    return json.dumps(message, separators=(",", ":"))
