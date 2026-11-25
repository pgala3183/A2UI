"""OpenUI Lang, parsed by hand (the Python twin of openui-parse.mjs).

OpenUI Lang (https://github.com/thesysdev/openui) writes UI as one statement
per line, ``id = Expression``:

    root = Stack([title, kpis], "column")
    title = Text("Network dashboard", "h2")
    kpis = Stack([bikes, rides], "row")
    bikes = Metric("Bikes docked", "49 / 100")

* a capitalised call is a component; arguments are positional and map to
  the component's parameters in order (the library defines the order);
* a lowercase name is a reference to another statement, and may point
  *forward*: ``root`` can name ``title`` before ``title`` exists, which is
  what lets a page paint the layout first and fill it in while streaming;
* literals are JSON: strings, numbers, true/false/null, [lists], {objects};
* a later statement with the same id replaces the earlier one, so an
  update can resend only the statements that changed.

The official packages (@openuidev/lang-core, @openuidev/react-lang) do this
with Zod-defined libraries and React. This file implements the core of the
language so every step of it is visible.
"""

from __future__ import annotations

import json
import re

TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
                   r'|(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<punct>[()\[\]{},:=]))')
HEAD = re.compile(r"^\s*([a-z_][A-Za-z0-9_]*)\s*=\s*([A-Z][A-Za-z0-9_]*)?")


class ParseError(ValueError):
    pass


def tokenize(line: str) -> list[tuple[str, object]]:
    tokens, pos = [], 0
    line = line.rstrip()
    while pos < len(line):
        match = TOKEN.match(line, pos)
        if not match or match.end() == pos:
            raise ParseError(f"unexpected character at {pos}: {line[pos:pos + 12]!r}")
        pos = match.end()
        kind = match.lastgroup
        text = match.group(kind)
        tokens.append((kind, json.loads(text) if kind in ("str", "num") else text))
    return tokens


class _Reader:
    def __init__(self, tokens):
        self.tokens, self.i = tokens, 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def take(self, value=None):
        kind, text = self.peek()
        if kind is None or (value is not None and text != value):
            raise ParseError(f"expected {value or 'a value'}, got {text!r}")
        self.i += 1
        return kind, text

    def expr(self):
        kind, text = self.take()
        if kind in ("str", "num"):
            return ("lit", text)
        if kind == "punct" and text == "[":
            items = self.items("]")
            return ("list", items)
        if kind == "punct" and text == "{":
            members = {}
            while self.peek()[1] != "}":
                key_kind, key = self.take()
                if key_kind not in ("str", "name"):
                    raise ParseError(f"bad object key {key!r}")
                self.take(":")
                members[key] = self.expr()
                if self.peek()[1] == ",":
                    self.take(",")
            self.take("}")
            return ("obj", members)
        if kind == "name":
            if text in ("true", "false", "null"):
                return ("lit", {"true": True, "false": False, "null": None}[text])
            if self.peek()[1] == "(":
                self.take("(")
                return ("call", text, self.items(")"))
            return ("ref", text)
        raise ParseError(f"unexpected {text!r}")

    def items(self, close):
        out = []
        while self.peek()[1] != close:
            out.append(self.expr())
            if self.peek()[1] == ",":
                self.take(",")
            elif self.peek()[1] != close:
                raise ParseError(f"expected ',' or {close!r}")
        self.take(close)
        return out


def parse_statement(line: str) -> tuple[str, tuple]:
    reader = _Reader(tokenize(line))
    kind, name = reader.take()
    if kind != "name" or not name[0].islower():
        raise ParseError("a statement starts with a lowercase id")
    reader.take("=")
    value = reader.expr()
    if reader.peek()[0] is not None:
        raise ParseError(f"unexpected {reader.peek()[1]!r} after the expression")
    return name, value


class Program:
    """Statements by id. ``feed`` accepts streamed text and keeps the incomplete last line aside."""

    def __init__(self):
        self.statements: dict[str, tuple] = {}
        self.buffer = ""

    def feed(self, chunk: str) -> list[tuple[str, str]]:
        """Returns the complete lines that arrived, as (id, line) pairs."""
        self.buffer += chunk
        done = []
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip() and not line.strip().startswith(("```", "#", "//")):
                done.append(line.strip())
        return done

    def add(self, line: str) -> str:
        sid, value = parse_statement(line)
        self.statements[sid] = value  # a later statement with the same id wins
        return sid

    def pending(self) -> dict | None:
        """What the incomplete line is about to define: {id, component, chars}."""
        match = HEAD.match(self.buffer)
        if not match:
            return None
        return {"id": match.group(1), "component": match.group(2), "chars": len(self.buffer)}

    def source(self) -> str:
        return "\n".join(f"{sid} = {unparse(v)}" for sid, v in self.statements.items())


def unparse(node) -> str:
    kind = node[0]
    if kind == "lit":
        return json.dumps(node[1])
    if kind == "ref":
        return node[1]
    if kind == "list":
        return "[" + ", ".join(unparse(n) for n in node[1]) + "]"
    if kind == "obj":
        return "{" + ", ".join(f"{json.dumps(k)}: {unparse(v)}" for k, v in node[1].items()) + "}"
    return f"{node[1]}(" + ", ".join(unparse(n) for n in node[2]) + ")"


def resolve(program: Program, library: dict, root: str = "root"):
    """Statements -> a tree of {type, id, props}. Unknown refs become {type: '__missing'}."""

    def value(node, owner: str, path: str, seen: frozenset):
        kind = node[0]
        if kind == "lit":
            return node[1]
        if kind == "list":
            return [value(n, owner, f"{path}.{i}", seen) for i, n in enumerate(node[1])]
        if kind == "obj":
            return {k: value(v, owner, f"{path}.{k}", seen) for k, v in node[1].items()}
        if kind == "ref":
            name = node[1]
            if name in seen:
                return {"type": "__cycle", "id": name}
            if name not in program.statements:
                return {"type": "__missing", "id": name}
            return value(program.statements[name], name, name, seen | {name})
        name, args = node[1], node[2]
        params = [p["name"] for p in library.get(name, {}).get("params", [])]
        props = {params[i] if i < len(params) else f"arg{i}": value(a, owner, f"{path}.{i}", seen) for i, a in enumerate(args)}
        return {"type": name, "id": path, "props": props}

    if root not in program.statements:
        return {"type": "__missing", "id": root}
    return value(program.statements[root], root, root, frozenset({root}))
