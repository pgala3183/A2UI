// The registry: the browser half of the catalog. Same names as catalog.py.
// A registry entry gets resolved props, rendered children and a ctx whose
// act(event) fires the element's "on" handler.

import * as w from '/common/components.mjs';
import { hash } from '/common/morph.mjs';

export const registry = {
  // static mode: whole widgets
  StationCard: (p) => w.stationCard(p),
  AlertBanner: (p) => w.alert({ level: p.level, text: p.text }),
  RideQuote: (p) => w.card({ title: 'Ride quote' }, [w.metric({ label: `${p.minutes} min${p.ebike ? ' e-bike' : ''}`, value: `$${Number(p.price).toFixed(2)}` })]),
  // declarative mode: primitives
  Card: (p, kids) => w.card({ title: p.title, subtitle: p.subtitle }, kids),
  Row: (p, kids) => w.row({ gap: p.gap ?? 'medium' }, kids),
  Column: (p, kids) => w.column({ gap: p.gap ?? 'medium' }, kids),
  Text: (p) => w.textBlock({ text: p.text, variant: p.variant }),
  Metric: (p) => w.metric({ label: p.label, value: p.value, delta: p.delta }),
  Table: (p) => w.table({ columns: p.columns ?? [], rows: p.rows ?? [] }),
  BarChart: (p) => w.barChart({ title: p.title, labels: p.labels ?? [], values: p.values ?? [] }),
  Badge: (p) => w.badge({ text: p.text, tone: p.tone }),
  Button: (p, kids, ctx) => w.button({ label: p.label, variant: p.variant }, () => ctx.act('press')),
  // open-ended and mixed: an HTML document streamed in chunks, mounted when complete
  HtmlArtifact: (p, kids, ctx) => {
    const html = (p.chunks ?? []).join('');
    if (!p.complete) {
      return w.card({ title: p.title ?? 'Artifact' }, [
        w.textBlock({ text: `generating... ${html.length} characters received`, variant: 'caption' }),
        w.h('pre', { class: 'source' }, html.slice(-600)),
      ]);
    }
    return ctx.frames.slot(ctx.id, html, { label: `HtmlArtifact "${p.title ?? ctx.id}" - model-written HTML (sandboxed)`, height: p.height ?? 280 });
  },
};

export const artifactSig = (p) => hash((p.chunks ?? []).join('') + String(p.complete));
