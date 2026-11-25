// Client side of the custom HtmlFrame component.
//
// The renderer asks the surface's FrameHost for a slot. After morph(), the
// FrameHost mounts the sandboxed iframe into the slot and pushes the surface's
// data model into it. A frame's genui.send(name, payload) comes back as an
// A2UI action envelope whose sourceComponentId is the HtmlFrame's id.

import { hash } from '/common/morph.mjs';

export const custom = {
  HtmlFrame(component, { frames }) {
    const label = `HtmlFrame "${component.title ?? component.id}" - model-written HTML in a sandboxed iframe`;
    return {
      el: frames.slot(component.id, component.html ?? '', { label, height: component.height ?? 280 }),
      sig: { html: hash(component.html ?? ''), title: component.title, height: component.height },
    };
  },
};
