// Re-render without losing live state.
//
// Renderers in these codelabs are simple: they rebuild the whole tree from the
// spec every time something changes. `morph` then updates the live DOM to
// match the new tree, keeping every element whose key and signature did not
// change. That matters for two kinds of element:
//
//   * inputs: a focused text field keeps its caret while the data model updates;
//   * sandboxed iframes: moving or replacing an iframe reloads it, which would
//     wipe whatever the user did inside the generated view.
//
// Renderers mark each component's root element with data-key (its id) and
// data-sig (a hash of its own props). Same key + same sig = keep the old node.
// Frames are placed through FrameHost slots, which morph never looks inside.

import { mountSandbox } from './sandbox.mjs';

export function hash(value) {
  const text = typeof value === 'string' ? value : JSON.stringify(value) ?? '';
  let h = 5381;
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

export function keyed(el, key, props) {
  el.dataset.key = key;
  el.dataset.sig = hash(props ?? {});
  return el;
}

const sameKind = (a, b) =>
  a.nodeType === b.nodeType && a.nodeName === b.nodeName && (a.dataset?.key ?? null) === (b.dataset?.key ?? null);

function morphNode(a, b) {
  if (a.nodeType === Node.TEXT_NODE) {
    if (a.data !== b.data) a.data = b.data;
    return a;
  }
  if (a.nodeType !== Node.ELEMENT_NODE) return b;
  if (a.dataset.sig !== b.dataset.sig) return b; // props changed: take the new element
  if (a.dataset.frame !== undefined || a.tagName === 'IFRAME') return a; // frames are opaque
  if (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.tagName === 'SELECT') {
    if (document.activeElement !== a && a.value !== b.value) a.value = b.value;
    if (a.checked !== b.checked) a.checked = b.checked;
    return a;
  }
  for (const name of a.getAttributeNames()) if (!b.hasAttribute(name)) a.removeAttribute(name);
  for (const name of b.getAttributeNames()) if (a.getAttribute(name) !== b.getAttribute(name)) a.setAttribute(name, b.getAttribute(name));
  morphChildren(a, [...b.childNodes]);
  return a;
}

export function morphChildren(parent, wanted) {
  const pool = [...parent.childNodes];
  const byKey = new Map();
  for (const node of pool) if (node.dataset?.key) byKey.set(node.dataset.key, node);
  const used = new Set();
  const result = wanted.map((b, i) => {
    const candidate = b.dataset?.key ? byKey.get(b.dataset.key) : pool[i];
    if (candidate && !used.has(candidate) && sameKind(candidate, b)) {
      used.add(candidate);
      return morphNode(candidate, b);
    }
    return b;
  });
  const keep = new Set(result);
  for (const node of pool) if (!keep.has(node)) node.remove(); // remove first, so nothing has to move
  let cursor = parent.firstChild;
  for (const node of result) {
    if (node === cursor) {
      cursor = cursor.nextSibling;
      continue;
    }
    parent.insertBefore(node, cursor);
  }
  while (cursor) {
    const next = cursor.nextSibling;
    cursor.remove();
    cursor = next;
  }
}

export function morph(container, children) {
  morphChildren(container, (Array.isArray(children) ? children : [children]).filter(Boolean));
}

// Owns the sandboxed iframes of one surface. A renderer asks for a slot; after
// morph, attach() mounts a sandbox into every new slot. send() pushes data.
export class FrameHost {
  constructor({ onAction } = {}) {
    this.onAction = onAction;
    this.mounts = new Map(); // key -> { slot, mount }
    this.pending = new Map(); // key -> html
  }

  slot(key, html, { label = 'generated region (sandboxed iframe)', height = 260 } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'genui-frame';
    const tag = document.createElement('div');
    tag.className = 'generated-label';
    tag.textContent = label;
    const slot = document.createElement('div');
    slot.dataset.frame = key;
    slot.dataset.key = `${key}:slot`;
    slot.dataset.sig = hash(html);
    slot.dataset.height = String(height);
    this.pending.set(key, html);
    wrap.append(tag, slot);
    return wrap;
  }

  attach(container, data) {
    for (const slot of container.querySelectorAll('[data-frame]')) {
      const key = slot.dataset.frame;
      const current = this.mounts.get(key);
      if (current && current.slot === slot) continue;
      current?.mount.destroy();
      const mount = mountSandbox(slot, this.pending.get(key) ?? '', {
        onAction: (name, payload) => this.onAction?.(key, name, payload),
        height: Number(slot.dataset.height),
        title: key,
      });
      this.mounts.set(key, { slot, mount });
    }
    for (const [key, { slot, mount }] of this.mounts) {
      if (!slot.isConnected) {
        mount.destroy();
        this.mounts.delete(key);
      }
    }
    if (data !== undefined) this.send(data);
  }

  send(data, key) {
    for (const [k, { mount }] of this.mounts) if (key === undefined || k === key) mount.send(data);
  }
}
