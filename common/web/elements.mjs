// Render a flat element map: { root: "id", elements: { id: { type, props, children } } }.
//
// This is the declarative shape that AG-UI state (theme 02), json-render
// (theme 04) and the harness render_ui tool (theme 06) all use. A registry
// maps each element type to a function that builds DOM with the shared
// widgets. Unknown types and missing children render as visible skeletons,
// never as exceptions, so a half-streamed spec still paints.

import * as w from './components.mjs';
import { morph, keyed, FrameHost } from './morph.mjs';

// registry entry: (props, children, ctx, element) => Node
export const BASE_REGISTRY = {
  Card: (p, kids) => w.card({ title: p.title, subtitle: p.subtitle }, kids),
  Row: (p, kids) => w.row({ gap: p.gap ?? 'medium' }, kids),
  Column: (p, kids) => w.column({ gap: p.gap ?? 'medium' }, kids),
  Text: (p) => w.textBlock({ text: p.text, variant: p.variant }),
  Markdown: (p) => w.markdown({ text: p.text }),
  Metric: (p) => w.metric({ label: p.label, value: p.value, delta: p.delta }),
  Table: (p) => w.table({ columns: p.columns ?? [], rows: p.rows ?? [] }),
  BarChart: (p) => w.barChart({ title: p.title, labels: p.labels ?? [], values: p.values ?? [], unit: p.unit }),
  Alert: (p) => w.alert({ level: p.level, text: p.text }),
  Badge: (p) => w.badge({ text: p.text, tone: p.tone }),
  Divider: () => w.divider(),
  StationCard: (p) => w.stationCard(p),
  Button: (p, kids, ctx) => w.button({ label: p.label, variant: p.variant }, () => ctx.act(p.action, p.params ?? {})),
};

export class ElementView {
  constructor(container, { registry = BASE_REGISTRY, onAction, resolveProps, frameLabel } = {}) {
    this.container = container;
    this.registry = registry;
    this.onAction = onAction;
    this.resolveProps = resolveProps ?? ((props) => props); // e.g. json-render's {$state: "/path"}
    this.frames = new FrameHost({ onAction: (key, name, payload) => onAction?.({ source: 'frame', element: key, action: name, params: payload }) });
    this.frameLabel = frameLabel;
    this.spec = null;
  }

  render(spec, frameData) {
    this.spec = spec;
    const root = spec?.root;
    const tree = root ? this.node(root, new Set()) : null;
    morph(this.container, tree ? [tree] : []);
    this.frames.attach(this.container, frameData);
  }

  node(id, ancestors) {
    const element = this.spec?.elements?.[id];
    if (!element) return keyed(w.skeleton(id, 'waiting for'), `missing:${id}`, {});
    if (ancestors.has(id)) return keyed(w.skeleton(id, 'cycle at'), `cycle:${id}`, {});
    const inner = new Set(ancestors).add(id);
    const props = this.resolveProps(element.props ?? {}, element);
    const build = this.registry[element.type];
    if (!build) return keyed(w.skeleton(id, `not in catalog: ${element.type}`), id, { type: element.type });
    const children = (Array.isArray(element.children) ? element.children : []).map((child) => this.node(child, inner));
    const ctx = {
      id,
      frames: this.frames,
      act: (action, params) => this.onAction?.({ source: 'element', element: id, action, params }),
    };
    const el = build(props, children, ctx, element);
    if (element.visible === false) el.hidden = true;
    return keyed(el, id, { type: element.type, props, on: element.on });
  }
}
