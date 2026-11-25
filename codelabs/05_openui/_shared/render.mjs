// Draw a resolved OpenUI Lang tree with the shared widgets.
//
// resolve() turns statements into {type, id, props}. A reference that has not
// arrived yet is {type: '__missing', id}: it renders as a skeleton, or as a
// progress line when the server says that statement is being written right now.

import * as w from '/common/components.mjs';
import { keyed, hash } from '/common/morph.mjs';

const isNode = (v) => v && typeof v === 'object' && !Array.isArray(v) && typeof v.type === 'string';
// A signature of a node's own props: nested nodes count only by id.
const sigOf = (props) => JSON.stringify(props, (k, v) => (isNode(v) && k !== '' ? `#${v.id}` : v));

export const registry = {
  Stack: (p, ctx) => (p.direction === 'row' ? w.row : w.column)({ gap: { s: 'small', m: 'medium', l: 'large' }[p.gap] ?? p.gap ?? 'medium' }, ctx.kids(p.children)),
  Card: (p, ctx) => w.card({ title: p.title }, ctx.kids(p.children)),
  Text: (p) => w.textBlock({ text: p.text, variant: p.variant }),
  Markdown: (p) => w.markdown({ text: p.text }),
  Metric: (p) => w.metric({ label: p.label, value: p.value, delta: p.delta }),
  BarChart: (p) => w.barChart({ title: p.title, labels: ctx0(p.labels), values: ctx0(p.values) }),
  Table: (p) => w.table({ columns: ctx0(p.columns), rows: ctx0(p.rows) }),
  Button: (p, ctx) => w.button({ label: p.label, variant: p.variant }, () => ctx.act(p.action, {})),
  StationCard: (p) => w.stationCard({ ...p, hours: ['6a', '7a', '8a', '9a', '10a', '11a', '12p', '1p', '2p', '3p', '4p', '5p', '6p'] }),
  AlertBanner: (p) => w.alert({ level: p.level, text: p.text }),
  RideQuote: (p) => w.card({ title: 'Ride quote' }, [w.metric({ label: `${p.minutes} min`, value: `$${Number(p.price).toFixed(2)}` })]),
  HtmlArtifact: (p, ctx, node) => {
    const doc = p.document;
    if (typeof doc !== 'string') { // the document statement is still streaming
      const info = ctx.pending.get(doc?.id);
      return w.card({ title: p.title }, [w.textBlock({ text: info ? `generating... ${info.chars} characters so far` : 'waiting for the document...', variant: 'caption' })]);
    }
    const tab = ctx.tabs.get(node.id) ?? 'rendered';
    const tabs = w.h('div', { class: 'tabs' }, ['rendered', 'raw'].map((t) =>
      w.h('button', { class: t === tab ? 'active' : '', onClick: () => ctx.setTab(node.id, t) }, t)));
    if (p.data && typeof p.data === 'object' && !isNode(p.data)) ctx.frameData.set(node.id, p.data);
    const body = tab === 'raw'
      ? w.h('pre', { class: 'source' }, doc)
      : ctx.frames.slot(node.id, doc, { label: `HtmlArtifact "${p.title}" - model-written HTML (sandboxed)`, height: 280 });
    return w.h('div', { class: 'artifact' }, tabs, body);
  },
};
function ctx0(v) { return Array.isArray(v) ? v : []; }

export function renderNode(node, ctx) {
  if (!isNode(node)) return w.textBlock({ text: String(node ?? '') });
  if (node.type === '__missing') {
    const info = ctx.pending.get(node.id);
    const label = info ? `writing ${info.component ?? 'statement'} "${node.id}" (${info.chars} chars)` : 'waiting for';
    return keyed(w.skeleton(node.id, label), `missing:${node.id}`, { label });
  }
  if (node.type === '__cycle') return keyed(w.skeleton(node.id, 'cycle at'), `cycle:${node.id}`, {});
  const build = registry[node.type];
  if (!build) return keyed(w.skeleton(node.id, `not in library: ${node.type}`), node.id, {});
  const local = { ...ctx, kids: (list) => (Array.isArray(list) ? list : []).map((child) => renderNode(child, ctx)) };
  const el = build(node.props, local, node);
  const sig = node.type === 'HtmlArtifact'
    ? { title: node.props.title, doc: typeof node.props.document === 'string' ? hash(node.props.document) : 'pending', tab: ctx.tabs.get(node.id), pending: ctx.pending.get(node.props.document?.id)?.chars }
    : sigOf(node.props);
  return keyed(el, node.id, sig);
}
