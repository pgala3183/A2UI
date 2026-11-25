"""OpenUI Lang on the server: libraries, prompts, and a statement gate.

A *library* says which components exist and the order of their positional
parameters. It generates the system prompt and validates each statement as
it streams. ``StatementGate`` forwards a line only when it parses and every
component call in it fits the library, so the browser renders nothing the
library does not allow.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

from openui_parse import ParseError, Program, parse_statement  # noqa: E402

CHECKS = {
    "string": lambda n: n[0] == "lit" and isinstance(n[1], str),
    "number": lambda n: n[0] == "lit" and isinstance(n[1], (int, float)) and not isinstance(n[1], bool),
    "text": lambda n: n[0] == "lit" and isinstance(n[1], (str, int, float)) and not isinstance(n[1], bool),
    "boolean": lambda n: n[0] == "lit" and isinstance(n[1], bool),
    "list": lambda n: n[0] == "list",
    "object": lambda n: n[0] == "obj",
    "component": lambda n: n[0] == "call",
    "any": lambda n: True,
}


def p(name: str, kind: str, description: str = "", optional: bool = False, enum=None) -> dict:
    return {"name": name, "type": kind, "description": description, "optional": optional, **({"enum": enum} if enum else {})}


def prompt(library: dict) -> str:
    lines = ["Write OpenUI Lang: one statement per line, `id = Expression`. The first statement is `root = ...`.",
             "Capitalised calls are components with positional arguments; lowercase names refer to other",
             "statements and may refer forward. Literals are JSON. Components:"]
    for name, spec in library.items():
        params = ", ".join(f"{x['name']}{'?' if x['optional'] else ''}: {'|'.join(map(repr, x['enum'])) if x.get('enum') else x['type']}"
                           for x in spec["params"])
        lines.append(f"- {name}({params}) - {spec['description']}")
    return "\n".join(lines)


def check_call(node, library: dict, where: str) -> list[str]:
    errors = []
    kind = node[0]
    if kind == "list":
        for i, item in enumerate(node[1]):
            errors += check_call(item, library, f"{where}[{i}]")
    elif kind == "obj":
        for key, item in node[1].items():
            errors += check_call(item, library, f"{where}.{key}")
    elif kind == "call":
        name, args = node[1], node[2]
        spec = library.get(name)
        if spec is None:
            return [f"{where}: unknown component {name}; the library has {', '.join(library)}"]
        params = spec["params"]
        required = [x for x in params if not x["optional"]]
        if len(args) < len(required):
            errors.append(f"{where}: {name} needs {', '.join(x['name'] for x in required)}")
        if len(args) > len(params):
            errors.append(f"{where}: {name} takes at most {len(params)} arguments")
        for param, arg in zip(params, args):
            if arg[0] == "ref":
                continue  # resolved later; may point forward
            if not CHECKS[param["type"]](arg):
                errors.append(f"{where}: {name}.{param['name']} must be {param['type']}")
            elif param.get("enum") and arg[1] not in param["enum"]:
                errors.append(f"{where}: {name}.{param['name']} must be one of {param['enum']}")
            errors += check_call(arg, library, f"{where}.{param['name']}")
    return errors


class StatementGate:
    def __init__(self, library: dict, extra_check=None):
        self.library = library
        self.program = Program()
        self.extra_check = extra_check  # fn(statement_id, node, program) -> list[str]

    def offer(self, line: str) -> list[str]:
        try:
            sid, node = parse_statement(line)
        except ParseError as error:
            return [f"parse error: {error}"]
        errors = check_call(node, self.library, sid)
        if not errors and self.extra_check:
            errors = self.extra_check(sid, node, self.program)
        if not errors:
            self.program.statements[sid] = node
        return errors

    def unresolved(self) -> list[str]:
        """References that no statement defines (checked once the stream ends)."""
        missing = set()

        def walk(node):
            if node[0] == "ref" and node[1] not in self.program.statements:
                missing.add(node[1])
            elif node[0] in ("list",):
                for n in node[1]:
                    walk(n)
            elif node[0] == "obj":
                for n in node[1].values():
                    walk(n)
            elif node[0] == "call":
                for n in node[2]:
                    walk(n)

        for node in self.program.statements.values():
            walk(node)
        return sorted(missing)


def stream_lines(chunks, splitter: Program):
    """Yield ("line", text) for each complete line, and ("pending", info) while a long line grows.

    ``splitter`` only splits text into lines; the gate's program holds the
    statements that were accepted.
    """
    reported = None  # (id, chars) of the last progress report
    for chunk in chunks:
        for line in splitter.feed(chunk):
            reported = None
            yield "line", line
        info = splitter.pending()
        if info and (reported is None or info["id"] != reported[0] or info["chars"] - reported[1] >= 400):
            reported = (info["id"], info["chars"])
            yield "pending", info
    if splitter.buffer.strip():
        yield "line", splitter.buffer.strip()
        splitter.buffer = ""


def generate(llm, system: str, messages: list[dict], gate: StatementGate):
    """Stream a model reply as SSE events: ('line'|'refused'|'pending'|'note', data)."""
    splitter = Program()
    chunks = (e["text"] for e in llm.stream(system, messages) if e["type"] == "text")
    for kind, value in stream_lines(chunks, splitter):
        if kind == "pending":
            yield "pending", value
            continue
        errors = gate.offer(value)
        yield ("refused", {"line": value[:120], "errors": errors}) if errors else ("line", {"line": value})
    yield "note", {"statements": len(gate.program.statements), "unresolved": gate.unresolved()}


def _calls(node, name):
    if node[0] == "call":
        if node[1] == name:
            yield node
        for arg in node[2]:
            yield from _calls(arg, name)
    elif node[0] == "list":
        for item in node[1]:
            yield from _calls(item, name)
    elif node[0] == "obj":
        for item in node[1].values():
            yield from _calls(item, name)


def artifact_policy(sid: str, node, program: Program) -> list[str]:
    """Check every HtmlArtifact document, whichever arrives first: the call or the string."""
    from genui_common.sandbox import check_html

    docs = []
    for statement in [node, *program.statements.values()]:
        for call in _calls(statement, "HtmlArtifact"):
            if len(call[2]) < 2:
                continue
            doc = call[2][1]
            if doc[0] == "lit" and statement is node:
                docs.append(doc[1])
            elif doc[0] == "ref" and doc[1] == sid and node[0] == "lit":
                docs.append(node[1])  # this line is the document an earlier call points to
            elif doc[0] == "ref" and statement is node and program.statements.get(doc[1], ("",))[0] == "lit":
                docs.append(program.statements[doc[1]][1])  # the document came first
    return [f"{sid}: {problem}" for doc in docs if isinstance(doc, str) for problem in check_html(doc)]


def make_app(step_dir: Path, library: dict, title: str):
    from genui_common.web import App

    app = App(step_dir / "page", {"/shared/": HERE}, title=title)
    app.get("/library")(lambda request: library)
    return app
