// A2UI on the client, without any DOM: surfaces, components and data models.
//
// A Processor receives envelopes in any order the server sends them and keeps,
// per surface, a Map of components (id -> component) and a data model (a JSON
// object addressed by JSON Pointer). Rendering is a separate module; this file
// can be tested in Node.

import { getPointer, setPointer, removePointer } from '/common/jsonpatch.mjs';

export const VERSION = 'v0.9';
const ENVELOPES = ['createSurface', 'updateComponents', 'updateDataModel', 'deleteSurface'];

export function messageKind(message) {
  const keys = ENVELOPES.filter((k) => message && Object.hasOwn(message, k));
  return keys.length === 1 ? keys[0] : null;
}

export class Surface {
  constructor(id, catalogId) {
    this.id = id;
    this.catalogId = catalogId;
    this.components = new Map();
    this.data = {};
  }

  apply(kind, body) {
    if (kind === 'updateComponents') {
      for (const component of body.components) this.components.set(component.id, component);
    } else if (kind === 'updateDataModel') {
      const path = body.path ?? '/';
      if (Object.hasOwn(body, 'value')) this.data = setPointer(this.data, path, structuredClone(body.value));
      else this.data = removePointer(this.data, path) ?? {};
    }
  }

  // A value is a literal or a binding {path: '/x'} into the data model.
  resolve(value) {
    if (value && typeof value === 'object' && !Array.isArray(value) && typeof value.path === 'string') {
      return getPointer(this.data, value.path);
    }
    return value;
  }

  set(path, value) {
    this.data = setPointer(this.data, path, value);
  }

  // Missing ids show where the stream has not caught up yet (progressive rendering).
  missing() {
    const out = [];
    for (const c of this.components.values()) {
      for (const id of [c.child, ...(Array.isArray(c.children) ? c.children : [])]) {
        if (id && !this.components.has(id)) out.push(id);
      }
    }
    if (!this.components.has('root')) out.unshift('root');
    return out;
  }

  // The client half of an action: resolve the context against the data model now.
  action(component) {
    const event = component.action?.event ?? {};
    const context = {};
    for (const [key, value] of Object.entries(event.context ?? {})) context[key] = this.resolve(value) ?? null;
    return {
      version: VERSION,
      action: { name: event.name, surfaceId: this.id, sourceComponentId: component.id, timestamp: new Date().toISOString(), context },
    };
  }
}

export class Processor {
  constructor() {
    this.surfaces = new Map();
  }

  // Returns {kind, surfaceId} so the caller knows what to re-render.
  process(message) {
    if (message?.version !== VERSION) throw new Error(`unsupported version ${message?.version}`);
    const kind = messageKind(message);
    if (!kind) throw new Error('not an A2UI envelope');
    const body = message[kind];
    const id = body.surfaceId;
    if (kind === 'createSurface') {
      this.surfaces.set(id, new Surface(id, body.catalogId));
    } else if (kind === 'deleteSurface') {
      this.surfaces.delete(id);
    } else {
      const surface = this.surfaces.get(id);
      if (!surface) throw new Error(`${kind} for unknown surface ${id}`);
      surface.apply(kind, body);
    }
    return { kind, surfaceId: id };
  }
}
