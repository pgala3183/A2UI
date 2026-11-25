"""Tools: what the model may call, how inputs are checked, what the user must approve.

A tool function returns either a string (the result the model reads) or a
pair ``(result, ui_events)``. UI events are how generative UI enters the
harness: the loop forwards them to every surface (terminal and web).

Permissions follow the usual harness pattern:
  "allow"  run without asking (reads, rendering)
  "ask"    pause the loop until the user approves or denies
  "deny"   never run; the model is told so
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from jsonschema import Draft202012Validator


class ToolError(Exception):
    """Raise inside a tool to return a readable error to the model."""


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    fn: Callable
    permission: str = "allow"
    _validator: Draft202012Validator = field(init=False, repr=False)

    def __post_init__(self):
        self._validator = Draft202012Validator(self.schema)

    def for_model(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.schema}

    def execute(self, args: dict) -> tuple[str, list[dict], bool]:
        """Returns (result text, ui events, is_error). Never raises for bad input."""
        errors = [f"{'/'.join(map(str, e.path)) or 'input'}: {e.message}" for e in self._validator.iter_errors(args)]
        if errors:
            return json.dumps({"error": "invalid input", "details": errors}), [], True
        try:
            out = self.fn(**args)
        except ToolError as error:
            return json.dumps({"error": str(error)}), [], True
        if isinstance(out, tuple):
            result, events = out
        else:
            result, events = out, []
        return (result if isinstance(result, str) else json.dumps(result)), events, False


class Registry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def add(self, name: str, description: str, schema: dict, permission: str = "allow"):
        """Decorator: register a function as a tool."""
        def register(fn):
            self.tools[name] = Tool(name, description, schema, fn, permission)
            return fn
        return register

    def for_model(self) -> list[dict]:
        return [t.for_model() for t in self.tools.values() if t.permission != "deny"]

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)


def obj(required: list[str] | None = None, **props) -> dict:
    """A small JSON Schema helper: obj(["a"], a={"type": "string"})."""
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}
