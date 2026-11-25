# Theme 05 · OpenUI Lang: a compact language for UI

[OpenUI Lang](https://github.com/thesysdev/openui) (from Thesys) writes UI as one statement per line, `id = Expression`:

```text
root = Card("Network dashboard", [kpis, chart])
kpis = Stack([bikes, rides], "row")
bikes = Metric("Bikes docked", "49 / 100")
rides = Metric("Rides today", 634, "+6%")
chart = BarChart("Bikes per station", names, counts)
names = ["Market St & 4th", "Ferry Building"]
counts = [3, 21]
```

- a capitalised call is a component; its arguments are **positional**, and the library defines their order;
- a lowercase name is a **reference** to another statement and may point **forward**: `root` names `kpis` before `kpis` exists, so a page can paint the layout first and fill it in while streaming;
- literals are JSON;
- a later statement with the same id **replaces** the earlier one, so an update can resend only what changed.

The official packages (`@openuidev/lang-core`, `@openuidev/react-lang`) do this with Zod-defined libraries and React. These codelabs implement the core of the language by hand, as twin parsers in Python (`openui_parse.py`) and JavaScript (`openui-parse.mjs`), so every step is visible.

## The four modes in OpenUI Lang

| Codelab | Mode | The library | New idea |
|---|---|---|---|
| [01_static](01_static/README.md) | static | three whole widgets | one statement; positional args; tokens next to JSON |
| [02_declarative](02_declarative/README.md) | declarative | layout primitives | forward references as skeletons; updates by redefining statements |
| [03_open_ended](03_open_ended/README.md) | open-ended | `HtmlArtifact(title, document, data)` | progress while a long line streams; Raw / Rendered tabs; data by reference |
| [04_mixed](04_mixed/README.md) | mixed | primitives + Markdown + `HtmlArtifact` | where the tokens go; the application answers in OpenUI Lang too |

## Shared code (`_shared/`)

| File | Role |
|---|---|
| `openui_parse.py` / `openui-parse.mjs` | tokenizer, statement parser, `Program` (streaming `feed`, `pending`), `resolve()` into `{type, id, props}` |
| `openui.py` | library helpers `p()`, `prompt()`, `StatementGate` (type checks per statement), `artifact_policy`, `generate()` (SSE events) |
| `render.mjs` | registry of components; skeletons and progress for unresolved references |
| `client.mjs` | the page loop: `line`, `pending`, `refused` events; program panel; first-paint timing |

`_shared/openui_parse.py`:

```python
        if kind == "ref":
            name = node[1]
            if name in seen:
                return {"type": "__cycle", "id": name}
            if name not in program.statements:
                return {"type": "__missing", "id": name}
```

A reference to a statement that has not arrived yet resolves to a `__missing` node, which renders as a skeleton.

## Run the theme

```bash
python run_all.py codelabs/05_openui
cd codelabs/05_openui/02_declarative && python demo.py
cd codelabs/05_openui/02_declarative && python server.py     # http://127.0.0.1:8502
```

Ports: 8501 (static), 8502 (declarative), 8503 (open-ended), 8504 (mixed).
