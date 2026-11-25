# Video script · Part 5 · OpenUI Lang (about 18 min)

## 0:00 What OpenUI Lang is (2 min)

**Screen:** `codelabs/05_openui/README.md`, the sample program.
**Say:** "OpenUI Lang writes UI as one statement per line. Capitalised calls are components with positional arguments; lowercase names are references, and they may point forward; literals are JSON; redefining an id replaces it. These codelabs parse it by hand, in Python and JavaScript twins."
**Open:** `_shared/openui_parse.py` `resolve()`: a missing reference becomes a `__missing` node.

## 2:00 Chapter 1 · Static: one statement (3 min)

**Run:** `cd codelabs/05_openui/01_static`, `python demo.py`: the generated prompt, the one-line answer, and the token comparison table.
**Code:** `server.py` LIBRARY with parameter order → `_shared/openui.py` `prompt()` and the gate's type checks → `_shared/openui-parse.mjs` positional args to props.
**Takeaway:** "Parameter names live in the library, not in every reply: that is where the tokens go."

## 5:00 Chapter 2 · Declarative: forward references (5 min)

**Run:** `$env:GENUI_DELAY = "0.05"`, `cd 02_declarative`, `python server.py`, http://127.0.0.1:8502, Run. Point at the skeletons, the "writing Metric" progress, and the program panel. Click "Only stations needing attention": four statements come back.
**Run:** `python demo.py`: the "missing now" column and the OpenUI vs JSON size.
**Code:** `server.py` root first → `Program.feed()` → `_shared/render.mjs` missing/progress → the action's four statements → redefinition in `add()`.
**Takeaway:** "Write root first, paint first; update by redefining."

## 10:00 Chapter 3 · Open-ended: HtmlArtifact (4 min)

**Run:** `03_open_ended`, http://127.0.0.1:8503, Run: progress while the doc line streams, then Rendered; switch to Raw. Book a ride.
**Code:** `server.py` three statements, document last → `stream_lines()` progress → `artifact_policy` (either order) → `render.mjs` tabs and data → the new `prices` statement.
**Takeaway:** "A long statement streams with progress; data flows in through a reference."

## 14:00 Chapter 4 · Mixed: library + HtmlArtifact (3 min)

**Run:** `04_mixed`, `python demo.py`: "the simulator document alone: ... (77%)". Then the page: apply a plan in the simulator; point at the five redefined statements and the simulator keeping its selection.
**Code:** the prompt rule → layout referencing `simDoc`/`simData` → `data_lines()` → source check → artifact signature by document only.
**Takeaway:** "Most of the cost is the artifact, so use it only where the library cannot do the job."

## 17:00 Wrap-up (1 min)

`python run_all.py codelabs/05_openui`.
