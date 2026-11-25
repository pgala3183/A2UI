// A SpecStream compiler: text chunks in, a growing spec out.
//
// The model writes one RFC 6902 JSON Patch operation per line (JSONL). Every
// complete line is applied to the spec at once, so the page can paint the
// root before the model has written the rest. This mirrors json-render's
// createSpecStreamCompiler: push(chunk) -> { spec, patches }.

import { applyOp } from '/common/jsonpatch.mjs';

export function createSpecStreamCompiler(initial = { root: null, elements: {}, state: {} }) {
  let spec = structuredClone(initial);
  let buffer = '';
  const applied = [];
  return {
    push(chunk) {
      buffer += chunk;
      const patches = [];
      let index;
      while ((index = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, index).trim();
        buffer = buffer.slice(index + 1);
        if (!line || line.startsWith('```')) continue;
        const op = JSON.parse(line);
        spec = applyOp(spec, op);
        patches.push(op);
        applied.push(op);
      }
      return { spec, patches };
    },
    apply(op) {
      spec = applyOp(spec, op);
      applied.push(op);
      return spec;
    },
    get spec() { return spec; },
    get applied() { return applied; },
  };
}
