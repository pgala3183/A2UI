"""The terminal surface: the harness's events drawn with rich.

The same ``ui`` events the web page renders become rich renderables here.
What a terminal cannot run (model-written HTML) degrades to a pointer to the
web surface, which serves the artifact with a sandboxing CSP header.
ASCII boxes keep the output safe on every Windows console and in log files.
"""

from __future__ import annotations

import json
import sys

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 3] + "..."


def bars(title, labels, values) -> Text:
    top = max([1, *[v for v in values if isinstance(v, (int, float))]])
    lines = [title] if title else []
    lines += [f"{str(label)[:18]:<18} {'#' * round(24 * value / top):<24} {value}" for label, value in zip(labels, values)]
    return Text("\n".join(lines))


def component(name: str, p: dict):
    if name == "Metric":
        return Panel(Text(f"{p.get('value')}" + (f"  {p['delta']}" if p.get("delta") else ""), style="bold"),
                     title=p.get("label"), box=box.ASCII, expand=False)
    if name == "Table":
        table = Table(*map(str, p.get("columns", [])), box=box.ASCII)
        for row in p.get("rows", []):
            table.add_row(*map(str, row))
        return table
    if name == "BarChart":
        return bars(p.get("title"), p.get("labels", []), p.get("values", []))
    if name == "Alert":
        return Panel(Text(str(p.get("text", ""))), title=p.get("level", "info"), box=box.ASCII)
    if name == "Text":
        return Text(str(p.get("text", "")), style="bold" if p.get("variant", "").startswith("h") else "")
    if name == "Badge":
        return Text(f"[{p.get('text')}]")
    if name == "Button":
        return Text(f"[ {p.get('label')} ]  ({p.get('action')})")
    if name == "Divider":
        return Text("-" * 40)
    if name == "GeneratedView":
        return Text(f"[interactive view '{p.get('artifact')}': open the web surface]", style="italic")
    return Text(f"[{name}]")


def spec(s: dict):
    def node(element_id, depth=0):
        element = s["elements"].get(element_id)
        if element is None or depth > 20:
            return Text(f"[missing {element_id}]")
        kids = [node(c, depth + 1) for c in element.get("children", [])]
        props = element.get("props", {})
        if element["type"] == "Card":
            return Panel(Group(*kids), title=props.get("title"), box=box.ASCII)
        if element["type"] == "Row":
            return Columns(kids, padding=(0, 2))
        if element["type"] == "Column":
            return Group(*kids)
        return component(element["type"], props)

    return node(s["root"])


class TerminalSurface:
    def __init__(self, console: Console | None = None):
        self.console = console or Console(highlight=False, emoji=False)
        self.in_text = False

    def handle(self, e: dict):
        c = self.console
        if e["type"] == "text":
            c.print(e["text"], end="", markup=False)
            self.in_text = True
            return
        if self.in_text:
            c.print()
            self.in_text = False
        if e["type"] == "tool_call":
            c.print(f"  -> {e['name']}({short(json.dumps(e['input']), 70)})", style="dim", markup=False)
        elif e["type"] == "tool_result":
            c.print(f"  <- {short(e['content'], 84)}", style="red" if e["is_error"] else "dim", markup=False)
        elif e["type"] == "ui":
            self.ui(e)
        elif e["type"] == "permission_request":
            c.print(Panel(Text(f"{e['name']} {short(json.dumps(e['input']), 240)}"), title="permission needed", box=box.ASCII))
        elif e["type"] == "error":
            c.print(f"  ! {e['message']}", style="red", markup=False)
        elif e["type"] == "done":
            c.print(f"  [done: {e['reason']}]", style="dim", markup=False)

    def ui(self, e: dict):
        kind = e["kind"]
        if kind == "component":
            self.console.print(component(e["component"], e["props"]))
        elif kind == "spec":
            self.console.print(spec(e["spec"]))
        elif kind == "html":
            self.console.print(Panel(Text(f"{e['title']}: interactive HTML, {len(e['html'])} chars.\n"
                                          f"Terminal fallback: open {e['artifact_url']} on the web surface."),
                                     title=f"view {e['view']}", box=box.ASCII))
        elif kind == "data":
            self.console.print(f"  [view {e['view']} received new data]", style="dim", markup=False)


def run_cli(make_harness, argv: list[str] | None = None, console: Console | None = None):
    """python cli.py "prompt" [--yes|--no]: one turn in the terminal, permissions asked on stdin."""
    argv = sys.argv[1:] if argv is None else argv
    flags = {a for a in argv if a.startswith("--")}
    prompt = " ".join(a for a in argv if not a.startswith("--")) or input("you> ")
    harness = make_harness()
    surface = TerminalSurface(console)
    events = harness.ask(prompt)
    while True:
        request = None
        for event in events:
            surface.handle(event)
            if event["type"] == "permission_request":
                request = event
        if request is None:
            return harness
        if "--yes" in flags:
            approve = True
        elif "--no" in flags:
            approve = False
        else:
            approve = input("approve? [y/N] ").strip().lower() == "y"
        events = harness.resume(request["id"], approve)
