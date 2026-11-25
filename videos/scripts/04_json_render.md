# Video script · Part 4 · json-render (about 18 min)

## 0:00 What json-render is (2 min)

**Screen:** `codelabs/04_json_render/README.md`, the spec example.
**Say:** "json-render describes UI as a flat spec. You declare a catalog once and use it three times: as the prompt, as the validator, as the registry. Props bind to state with $state, elements handle events with on.press, and setState runs in the browser. Specs stream as JSON Patch lines."
**Say:** "The library uses Zod and React; these codelabs implement the same contract without a build step."

## 2:00 Chapter 1 · Static: a catalog of widgets (3 min)

**Run:** `cd codelabs/04_json_render/01_static`, `python demo.py`: use 1 (prompt), use 2 (validator error then fix), use 3 (registry in the browser).
**Code:** `agent.py` `CATALOG` → `_shared/catalog.py` `prompt()` and `check_element()` → `server.py` "exactly one widget" → `_shared/registry.mjs`.
**Takeaway:** "One catalog, three uses; static is a catalog of whole widgets."

## 5:00 Chapter 2 · Declarative: streamed patches and $state (5 min)

**Run:** `02_declarative`, `python demo.py`: the numbered patch stream and "first paint needs patches 1-2". Then `$env:GENUI_DELAY = "0.05"`, `python server.py`, http://127.0.0.1:8402, Run: skeletons, then numbers. Click Refresh: one state patch.
**Code:** `agent.py` ops with `$state` → `server.py` PatchGate → `_shared/client.mjs` apply + first paint → `_shared/spec.mjs` `resolve()` → Refresh as a state diff → `_shared/stream.mjs`.
**Takeaway:** "Stream the spec, bind the numbers, and an update is a state patch."

## 10:00 Chapter 3 · Open-ended: HtmlArtifact in chunks (4 min)

**Run:** `03_open_ended`, http://127.0.0.1:8403, Run: "generating... N characters", then the calculator. Book a ride.
**Show:** in `demo.py` output, the gate accepting the element and refusing `complete: true` for a bad document.
**Code:** `agent.py` chunk appends with `"-"` and `html_policy()` → `_shared/registry.mjs` HtmlArtifact progress/slot → `server.py` booking as `/state/message`.
**Takeaway:** "JSON Patch can stream a document; the gate decides when it is complete."

## 14:00 Chapter 4 · Mixed: setState, server actions, two renderers (3 min)

**Run:** `04_mixed`, http://127.0.0.1:8404, Run. Toggle the table (point at zero requests in the wire panel). Apply a plan in the simulator (state patches). Open http://127.0.0.1:8404/text.
**Code:** `agent.py` toggle with `setState` and `$not`, `visible` binding → `_shared/spec.mjs` setState branch → `server.py` rebalance only from the artifact → `render_text.py`.
**Takeaway:** "One spec, two renderers; decide which state lives only in the browser."

## 17:00 Wrap-up (1 min)

`python run_all.py codelabs/04_json_render`.
