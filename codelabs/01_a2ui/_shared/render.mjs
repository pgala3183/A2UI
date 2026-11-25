// Draw an A2UI surface with the shared DOM widgets.
//
// The renderer walks the flat component map from "root", resolving each
// child id as it goes. An id that has not arrived yet becomes a skeleton, so
// a half-streamed surface still paints. Every re-render goes through morph(),
// which keeps unchanged elements (and live iframes) in place.

import { card, row, column, textBlock, button, textField, checkbox, divider, skeleton } from '/common/components.mjs';
import { morph, keyed, FrameHost } from '/common/morph.mjs';

// "# Title" -> {text: "Title", variant: "h1"}; A2UI Text allows markdown headings.
export function heading(text, variant) {
  const value = text === undefined || text === null ? '' : String(text);
  const match = value.match(/^(#{1,5})\s+(.*)$/);
  if (match) return { text: match[2], variant: variant && variant !== 'body' ? variant : `h${match[1].length}` };
  return { text: value, variant: variant ?? 'body' };
}

export class SurfaceView {
  // custom: { ComponentName: (component, ctx) => ({ el, sig }) } for catalog extensions.
  constructor(surface, container, { onAction, custom = {} } = {}) {
    this.surface = surface;
    this.container = container;
    this.onAction = onAction;
    this.custom = custom;
    this.frames = new FrameHost({
      onAction: (key, name, payload) =>
        onAction?.({
          version: 'v0.9',
          action: { name, surfaceId: surface.id, sourceComponentId: key, timestamp: new Date().toISOString(), context: payload },
        }),
    });
  }

  render() {
    morph(this.container, [this.node('root', new Set())]);
    this.frames.attach(this.container, this.surface.data); // new frames mount; every frame gets the data model
  }

  node(id, ancestors) {
    const s = this.surface;
    const c = s.components.get(id);
    if (!c) return keyed(skeleton(id, 'waiting for'), `missing:${id}`, {});
    if (ancestors.has(id)) return keyed(skeleton(id, 'cycle at'), `cycle:${id}`, {});
    const inner = new Set(ancestors).add(id);
    const child = (childId) => this.node(childId, inner);
    const r = (value) => s.resolve(value);
    let el;
    let sig;
    switch (c.component) {
      case 'Text': {
        sig = heading(r(c.text), c.variant);
        el = textBlock(sig);
        break;
      }
      case 'Card':
        el = card({}, [child(c.child)]);
        sig = {};
        break;
      case 'Column':
      case 'Row': {
        const layout = c.component === 'Row' ? row : column;
        el = layout({}, (Array.isArray(c.children) ? c.children : []).map(child));
        if (c.align) el.style.alignItems = { start: 'flex-start', end: 'flex-end' }[c.align] ?? c.align;
        sig = { align: c.align };
        break;
      }
      case 'Button': {
        const label = heading(r(s.components.get(c.child)?.text) ?? c.child).text;
        el = button({ label, variant: c.variant === 'borderless' ? 'secondary' : 'primary' }, () => this.onAction?.(s.action(c)));
        sig = { label, action: c.action, variant: c.variant };
        break;
      }
      case 'TextField': {
        const path = c.value?.path;
        el = textField({ label: r(c.label), value: r(c.value) ?? '', multiline: c.variant === 'longText' }, (value) => {
          if (path) {
            s.set(path, value); // two-way binding: the input writes into the data model
            this.render();
          }
        });
        sig = { label: r(c.label), path, variant: c.variant };
        break;
      }
      case 'CheckBox': {
        const path = c.value?.path;
        el = checkbox({ label: r(c.label), checked: r(c.value) }, (checked) => {
          if (path) {
            s.set(path, checked);
            this.render();
          }
        });
        sig = { label: r(c.label), path };
        break;
      }
      case 'Divider':
        el = divider();
        sig = {};
        break;
      default: {
        const custom = this.custom[c.component];
        ({ el, sig } = custom ? custom(c, { surface: s, frames: this.frames, child }) : { el: skeleton(id, `not in catalog: ${c.component}`), sig: {} });
      }
    }
    if (c.weight) el.style.flex = String(c.weight);
    return keyed(el, id, sig);
  }
}
