# Theme 04 · json-render: one catalog, three uses

[json-render](https://github.com/vercel-labs/json-render) (from Vercel Labs) describes UI as a flat spec and asks you to declare, once, which components and actions exist. That declaration, the **catalog**, is used three times: as the model's **prompt**, as the **validator** for what the model returns, and as the **registry** that maps names to rendering code.

```json
{
  "root": "dash",
  "elements": {
    "dash": {"type": "Card", "props": {"title": "Network dashboard"}, "children": ["m1"]},
    "m1": {"type": "Metric", "props": {"label": "Bikes", "value": {"$state": "/summary/bikes"}},
           "on": {"press": {"action": "refresh", "params": {}}}}
  },
  "state": {"summary": {"bikes": 49}}
}
```

- props may bind to state with `{"$state": "/json/pointer"}`;
- elements handle events with `"on": {"press": {"action", "params"}}`;
- the built-in action `setState` changes state in the browser, without a round trip;
- specs stream as RFC 6902 JSON Patch lines ("SpecStream"), so the page paints before the model finishes.

The library defines catalogs with Zod and renders with React (plus targets such as React Native and Ink for terminals). These codelabs implement the same contract without a build step: JSON Schema in Python (`catalog.py`) and a DOM registry in the browser (`registry.mjs`). The concepts and data shapes match; the API names are the library's where it helps (`createSpecStreamCompiler`, `setState`).

## The four modes in json-render

| Codelab | Mode | The catalog | New idea |
|---|---|---|---|
| [01_static](01_static/README.md) | static | three whole widgets | prompt + validator + registry from one catalog; a one-element spec |
| [02_declarative](02_declarative/README.md) | declarative | layout primitives | streamed JSON Patch, `$state` bindings, first paint, state-only updates |
| [03_open_ended](03_open_ended/README.md) | open-ended | `HtmlArtifact` only | a document streamed as chunks with `"-"` appends; the gate holds back `complete` |
| [04_mixed](04_mixed/README.md) | mixed | primitives + `HtmlArtifact` | `setState` (local) vs `rebalance` (server); a second renderer for the terminal |

## Shared code (`_shared/`)

| File | Role |
|---|---|
| `catalog.py` | `Catalog(components, actions)`: `prompt()` and `check()`; `dyn()` for `$state`-bindable props |
| `jr.py` | `PRIMITIVES`, `HTML_ARTIFACT`, `patch_lines()`, `PatchGate` (applies an op only if the spec still validates) |
| `spec.mjs` | `resolve()` for `$state`/`$not`, `SpecView` with `setState` built in |
| `registry.mjs` | the browser half of the catalog, by the same names |
| `stream.mjs` | `createSpecStreamCompiler()`: text chunks in, a growing spec out |
| `client.mjs` | the page loop, with first-paint timing |

`_shared/jr.py`:

```python
        try:
            candidate = jsonpatch.apply_patch(self.spec, [op])
        except jsonpatch.PatchError as error:
            return [f"{path}: {error}"]
```

The gate applies each operation to a copy of the spec and keeps it only if the result still validates.

## Run the theme

```bash
python run_all.py codelabs/04_json_render
cd codelabs/04_json_render/02_declarative && python demo.py
cd codelabs/04_json_render/04_mixed && python server.py     # http://127.0.0.1:8404, and /text
```

Ports: 8401 (static), 8402 (declarative), 8403 (open-ended), 8404 (mixed).
