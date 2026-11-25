# Theme 01 · A2UI: structure and data as two streams

[A2UI](https://a2ui.org) (Agent-to-User Interface, from Google) sends a user interface as a stream of JSON messages. The client keeps two things per **surface**: a flat map of components joined by ids, and a **data model** addressed by JSON Pointer. Structure and data arrive in separate messages, so data can change without resending the layout.

```json
{"version": "v0.9", "createSurface":    {"surfaceId": "s1", "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json"}}
{"version": "v0.9", "updateComponents": {"surfaceId": "s1", "components": [{"id": "root", "component": "Card", "child": "t"}, {"id": "t", "component": "Text", "text": {"path": "/station/name"}}]}}
{"version": "v0.9", "updateDataModel":  {"surfaceId": "s1", "path": "/station", "value": {"name": "Market St & 4th"}}}
{"version": "v0.9", "deleteSurface":    {"surfaceId": "s1"}}
```

The client answers with one envelope, `{"version": "v0.9", "action": {"name", "surfaceId", "sourceComponentId", "context"}}`, when a user triggers a component's action. A2UI is transport-agnostic; these codelabs carry it over Server-Sent Events.

## The four modes in A2UI

| Codelab | Mode | What the model writes | New idea |
|---|---|---|---|
| [01_static](01_static/README.md) | static | one tool call: which hand-written template | structure once, then only `updateDataModel` |
| [02_declarative](02_declarative/README.md) | declarative | `updateComponents` from the Basic Catalog | validation errors become the next prompt; skeletons while streaming; two-way binding |
| [03_open_ended](03_open_ended/README.md) | open-ended | one `HtmlFrame` holding a full HTML document | a custom catalog; the data model feeds a sandboxed iframe |
| [04_mixed](04_mixed/README.md) | mixed | Basic Catalog components + one `HtmlFrame` | one data model drives both halves; the iframe keeps its state |

A2UI is declarative by design. The static and open-ended modes show how far the protocol stretches in each direction: fixed templates that only receive data, and a custom catalog whose one component is a sandboxed document.

## Shared code (`_shared/`)

| File | Role |
|---|---|
| `a2ui.py` | envelope builders, the Basic Catalog subset as JSON Schema, `Catalog.prompt()`, `Mirror` (server-side validation per surface), `jsonl()` stream splitter |
| `htmlframe.py` / `htmlframe.mjs` | the custom `HtmlFrame` component: content policy on the server, sandbox slot on the client |
| `surface.mjs` | client state without a DOM: `Processor`, `Surface`, binding resolution, action envelopes |
| `render.mjs` | `SurfaceView`: walks the component map from `root`, skeletons for missing ids, re-renders with `morph()` |
| `client.mjs` | the page loop: `POST /run` and `POST /action`, both answered with SSE |

`_shared/surface.mjs`:

```js
  apply(kind, body) {
    if (kind === 'updateComponents') {
      for (const component of body.components) this.components.set(component.id, component);
    } else if (kind === 'updateDataModel') {
      const path = body.path ?? '/';
      if (Object.hasOwn(body, 'value')) this.data = setPointer(this.data, path, structuredClone(body.value));
      else this.data = removePointer(this.data, path) ?? {};
    }
  }
```

Components go into a `Map` keyed by id; data goes through a pointer. The nested tree never travels on the wire; the renderer rebuilds it from `root` at paint time.

## Run the theme

```bash
python run_all.py codelabs/01_a2ui            # tests
cd codelabs/01_a2ui/01_static && python demo.py   # one codelab, recorded output + screenshot
cd codelabs/01_a2ui/01_static && python server.py # interactive: http://127.0.0.1:8101
```

Ports: 8101 (static), 8102 (declarative), 8103 (open-ended), 8104 (mixed).
