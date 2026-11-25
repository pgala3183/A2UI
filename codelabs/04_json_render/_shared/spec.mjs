// json-render in the browser: resolve bindings, run actions, render a spec.
//
//   {"$state": "/path"}            a prop bound to spec.state
//   "visible": {"$state": "/x"}    an element shown only when state is truthy
//   "on": {"press": {...}}         an event handler: setState runs here; any other
//                                  action goes to the server (onAction)
//
// The library does this with React (<Renderer spec registry />) and hooks;
// here a registry of DOM builders plays that role so no build step is needed.

import { getPointer, setPointer } from '/common/jsonpatch.mjs';
import { ElementView } from '/common/elements.mjs';

export function resolve(value, state) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    if (typeof value.$state === 'string') return getPointer(state, value.$state);
    if (value.$not) return !resolve(value.$not, state);
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, resolve(v, state)]));
  }
  if (Array.isArray(value)) return value.map((v) => resolve(v, state));
  return value;
}

export class SpecView {
  constructor(container, { registry, onAction }) {
    this.spec = { root: null, elements: {}, state: {} };
    this.onAction = onAction;
    this.view = new ElementView(container, {
      registry,
      resolveProps: (props) => resolve(props, this.spec.state ?? {}),
      onAction: (event) => this.dispatch(event),
    });
  }

  // Elements call ctx.act('press') -> the element's "on.press" handler runs here.
  dispatch({ source, element, action, params }) {
    if (source === 'frame') return this.onAction?.({ action, params, element }); // from a sandboxed artifact
    const handler = this.spec.elements[element]?.on?.[action];
    if (!handler) return undefined;
    const resolved = resolve(handler.params ?? {}, this.spec.state ?? {});
    if (handler.action === 'setState') { // built in: no server, no model
      this.spec.state = setPointer(structuredClone(this.spec.state ?? {}), resolved.statePath, resolved.value);
      this.render();
      return undefined;
    }
    return this.onAction?.({ action: handler.action, params: resolved, element });
  }

  render() {
    const visible = structuredClone(this.spec);
    for (const element of Object.values(visible.elements ?? {})) {
      if (element.visible !== undefined) element.visible = Boolean(resolve(element.visible, this.spec.state ?? {}));
    }
    this.view.render(visible, this.spec.state);
  }
}
