// The DOM widgets every codelab draws with.
//
// Each technology describes UI differently (A2UI components, AG-UI tool
// calls, json-render elements, OpenUI Lang statements...). Their renderers all
// end here, so the same "Metric" looks the same everywhere and a codelab's
// renderer only has to translate its own format into these calls.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs ?? {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key === 'style' && typeof value === 'object') Object.assign(el.style, value);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else el.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === undefined || child === null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const text = (value) => (value === undefined || value === null ? '' : String(value));

export function card({ title, subtitle } = {}, children = []) {
  return h('section', { class: 'w-card' },
    title ? h('h3', { class: 'w-card-title' }, text(title)) : null,
    subtitle ? h('div', { class: 'w-muted' }, text(subtitle)) : null,
    h('div', { class: 'w-card-body' }, children));
}

export function row({ gap = 'medium', align } = {}, children = []) {
  return h('div', { class: `w-row gap-${gap}`, style: align ? { alignItems: align } : null }, children);
}

export function column({ gap = 'medium' } = {}, children = []) {
  return h('div', { class: `w-column gap-${gap}` }, children);
}

export function textBlock({ text: value, variant = 'body' } = {}) {
  const tag = { h1: 'h1', h2: 'h2', h3: 'h3', heading: 'h2' }[variant] ?? 'p';
  return h(tag, { class: `w-text w-text-${variant}` }, text(value));
}

export function metric({ label, value, delta, tone } = {}) {
  const d = text(delta);
  const trend = tone ?? (d.startsWith('-') ? 'down' : d ? 'up' : 'flat');
  return h('div', { class: 'w-metric' },
    h('div', { class: 'w-metric-label' }, text(label)),
    h('div', { class: 'w-metric-value' }, text(value)),
    d ? h('div', { class: `w-metric-delta ${trend}` }, d) : null);
}

export function table({ columns = [], rows = [] } = {}) {
  return h('table', { class: 'w-table' },
    h('thead', {}, h('tr', {}, columns.map((c) => h('th', {}, text(c))))),
    h('tbody', {}, rows.map((r) => h('tr', {}, (Array.isArray(r) ? r : columns.map((c) => r[c])).map((v) => h('td', {}, text(v)))))));
}

export function barChart({ title, labels = [], values = [], unit = '' } = {}) {
  const max = Math.max(1, ...values.map(Number).filter(Number.isFinite));
  return h('figure', { class: 'w-chart' },
    title ? h('figcaption', {}, text(title)) : null,
    h('div', { class: 'w-bars' }, labels.map((label, i) => {
      const v = Number(values[i] ?? 0);
      return h('div', { class: 'w-bar', title: `${label}: ${v}${unit}` },
        h('span', { class: 'w-bar-value' }, Number.isFinite(v) ? String(v) : ''),
        h('span', { class: 'w-bar-fill', style: { height: `${Math.round((100 * (Number.isFinite(v) ? v : 0)) / max)}%` } }),
        h('span', { class: 'w-bar-label' }, text(label)));
    })));
}

export function button({ label, variant = 'primary', disabled } = {}, onClick) {
  return h('button', { class: `w-button ${variant}`, disabled, onClick }, text(label));
}

export function textField({ label, value = '', placeholder, multiline } = {}, onInput) {
  const input = h(multiline ? 'textarea' : 'input', { class: 'w-input', placeholder, rows: multiline ? 3 : null });
  input.value = text(value);
  input.addEventListener('input', () => onInput?.(input.value));
  return h('label', { class: 'w-field' }, h('span', {}, text(label)), input);
}

export function checkbox({ label, checked } = {}, onChange) {
  const box = h('input', { type: 'checkbox' });
  box.checked = Boolean(checked);
  box.addEventListener('change', () => onChange?.(box.checked));
  return h('label', { class: 'w-check' }, box, h('span', {}, text(label)));
}

export function badge({ text: value, tone = 'neutral' } = {}) {
  return h('span', { class: `w-badge ${tone}` }, text(value));
}

export function alert({ level = 'info', text: value } = {}) {
  return h('div', { class: `w-alert ${level}`, role: 'status' }, text(value));
}

export function divider() {
  return h('hr', { class: 'w-divider' });
}

export function markdown({ text: value = '' } = {}) {
  // A deliberately small subset: **bold**, `code`, and paragraphs. Text only, no HTML.
  const block = h('div', { class: 'w-markdown' });
  for (const para of text(value).split(/\n{2,}/)) {
    const p = h('p');
    for (const part of para.split(/(\*\*[^*]+\*\*|`[^`]+`)/)) {
      if (part.startsWith('**') && part.endsWith('**')) p.append(h('strong', {}, part.slice(2, -2)));
      else if (part.startsWith('`') && part.endsWith('`')) p.append(h('code', {}, part.slice(1, -1)));
      else p.append(document.createTextNode(part));
    }
    block.append(p);
  }
  return block;
}

// A placeholder for a part of the UI that has not arrived yet (streaming).
export function skeleton(id, reason = 'loading') {
  return h('div', { class: 'w-skeleton', dataset: { missing: id } }, `${reason}: ${id}`);
}

// A pre-built, fixed widget: what "static" generative UI selects and fills.
export function stationCard({ name, bikes = 0, capacity = 1, docks, status, hourly = [], hours = [] } = {}) {
  const fill = Math.round((100 * Number(bikes)) / Math.max(1, Number(capacity)));
  const tone = fill <= 20 ? 'bad' : fill >= 85 ? 'warn' : 'good';
  return h('section', { class: 'w-card w-station' },
    h('div', { class: 'w-row gap-small', style: { justifyContent: 'space-between', alignItems: 'center' } },
      h('h3', { class: 'w-card-title' }, text(name)),
      status ? badge({ text: status, tone }) : null),
    h('div', { class: 'w-gauge' }, h('span', { class: `w-gauge-fill ${tone}`, style: { width: `${fill}%` } })),
    h('div', { class: 'w-row gap-large' },
      metric({ label: 'Bikes', value: bikes, tone: 'flat' }),
      metric({ label: 'Free docks', value: docks ?? Number(capacity) - Number(bikes), tone: 'flat' }),
      metric({ label: 'Full', value: `${fill}%`, tone: 'flat' })),
    hourly.length ? barChart({ title: 'Rides per hour', labels: hours.length ? hours : hourly.map((_, i) => i), values: hourly }) : null);
}
