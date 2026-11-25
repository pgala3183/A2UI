// RFC 6901 JSON Pointer + RFC 6902 add/replace/remove/test.
// The twin of common/genui_common/jsonpatch.py, with the same safety rules.

const FORBIDDEN = new Set(['__proto__', 'constructor', 'prototype']);

export function parsePointer(pointer) {
  if (pointer === '' || pointer === '/') return [];
  if (!pointer.startsWith('/')) throw new Error(`pointer must start with '/': ${pointer}`);
  const tokens = pointer.slice(1).split('/').map((t) => t.replace(/~1/g, '/').replace(/~0/g, '~'));
  for (const token of tokens) if (FORBIDDEN.has(token)) throw new Error(`forbidden key ${token}`);
  return tokens;
}

function index(list, token, allowEnd) {
  if (token === '-' && allowEnd) return list.length;
  if (!/^\d+$/.test(token)) throw new Error(`bad list index ${token}`);
  const i = Number(token);
  if (i > list.length || (i === list.length && !allowEnd)) throw new Error(`index ${i} out of range`);
  return i;
}

export function getPointer(doc, pointer, fallback) {
  let node = doc;
  for (const token of parsePointer(pointer)) {
    if (Array.isArray(node)) {
      if (!/^\d+$/.test(token) || Number(token) >= node.length) return fallback;
      node = node[Number(token)];
    } else if (node && typeof node === 'object' && Object.hasOwn(node, token)) {
      node = node[token];
    } else {
      return fallback;
    }
  }
  return node;
}

function parentOf(doc, tokens, create) {
  let node = doc;
  for (const token of tokens.slice(0, -1)) {
    if (Array.isArray(node)) node = node[index(node, token, false)];
    else if (node && typeof node === 'object') {
      if (!Object.hasOwn(node, token)) {
        if (!create) throw new Error(`missing parent ${token}`);
        node[token] = {};
      }
      node = node[token];
    } else throw new Error('cannot descend into a value');
  }
  return node;
}

// Upsert: create missing objects on the way (A2UI updateDataModel semantics).
export function setPointer(doc, pointer, value) {
  const tokens = parsePointer(pointer);
  if (!tokens.length) return value;
  const parent = parentOf(doc, tokens, true);
  const last = tokens.at(-1);
  if (Array.isArray(parent)) {
    const i = index(parent, last, true);
    if (i === parent.length) parent.push(value);
    else parent[i] = value;
  } else parent[last] = value;
  return doc;
}

export function removePointer(doc, pointer) {
  const tokens = parsePointer(pointer);
  if (!tokens.length) return undefined;
  const parent = parentOf(doc, tokens, false);
  const last = tokens.at(-1);
  if (Array.isArray(parent)) parent.splice(index(parent, last, false), 1);
  else delete parent[last];
  return doc;
}

const clone = (v) => (v === undefined ? v : structuredClone(v));

export function applyOp(doc, op) {
  const tokens = parsePointer(op.path);
  switch (op.op) {
    case 'add': {
      if (!tokens.length) return clone(op.value);
      const parent = parentOf(doc, tokens, false);
      if (Array.isArray(parent)) parent.splice(index(parent, tokens.at(-1), true), 0, clone(op.value));
      else parent[tokens.at(-1)] = clone(op.value);
      return doc;
    }
    case 'replace':
      if (getPointer(doc, op.path, undefined) === undefined) throw new Error(`nothing to replace at ${op.path}`);
      return setPointer(doc, op.path, clone(op.value));
    case 'remove':
      return removePointer(doc, op.path);
    case 'test':
      if (JSON.stringify(getPointer(doc, op.path)) !== JSON.stringify(op.value)) throw new Error(`test failed at ${op.path}`);
      return doc;
    default:
      throw new Error(`unsupported op ${op.op}`);
  }
}

export function applyPatch(doc, ops) {
  let result = clone(doc);
  for (const op of ops) result = applyOp(result, op);
  return result;
}
