// The view kit: everything an MCP App view needs, inlined into each view by
// the server (load_view), because a view runs in an opaque-origin iframe whose
// CSP forbids loading scripts. It plays the role of the official
// @modelcontextprotocol/ext-apps "App" class plus a small widget library.
//
//   viewKit.app           the app side of the host bridge (JSON-RPC over postMessage)
//   viewKit.w / h         widgets that build DOM
//   viewKit.renderSpec    draw a flat element map {root, elements}
//   viewKit.mountGenerated  a nested sandboxed iframe for model-written HTML
(() => {
  // ---- 1. the bridge: requests have ids, notifications do not ----------------
  let nextId = 0;
  const pending = new Map();
  const handlers = {};
  const send = (message) => window.parent.postMessage(message, '*');
  const request = (method, params) =>
    new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      send({ jsonrpc: '2.0', id, method, params });
    });
  const notify = (method, params) => send({ jsonrpc: '2.0', method, params });

  window.addEventListener('message', (event) => {
    if (event.source !== window.parent) return; // only the host
    const msg = event.data;
    if (!msg || msg.jsonrpc !== '2.0') return;
    if (msg.id !== undefined && !msg.method) { // a response to one of our requests
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p?.reject(new Error(msg.error.message));
      else p?.resolve(msg.result);
      return;
    }
    const fn = handlers[msg.method];
    if (msg.id !== undefined) { // a request from the host (e.g. ui/resource-teardown)
      Promise.resolve(fn ? fn(msg.params ?? {}) : {}).then((result) => send({ jsonrpc: '2.0', id: msg.id, result: result ?? {} }));
    } else fn?.(msg.params ?? {});
  });

  const app = {
    on(method, fn) { handlers[method] = fn; },
    async connect(appInfo) {
      const init = await request('ui/initialize', {
        appInfo, appCapabilities: { availableDisplayModes: ['inline'] }, protocolVersion: '2025-06-18',
      });
      notify('ui/notifications/initialized', {});
      new ResizeObserver(() => notify('ui/notifications/size-changed', {
        width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight,
      })).observe(document.documentElement);
      return init;
    },
    callServerTool: (name, args) => request('tools/call', { name, arguments: args ?? {} }),
    sendMessage: (text) => request('ui/message', { role: 'user', content: { type: 'text', text } }),
    openLink: (url) => request('ui/open-link', { url }),
    updateModelContext: (text, structuredContent) =>
      request('ui/update-model-context', { content: [{ type: 'text', text }], structuredContent }),
  };

  // ---- 2. widgets -------------------------------------------------------------
  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs ?? {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else el.setAttribute(k, v);
    }
    for (const c of children.flat(Infinity)) if (c !== undefined && c !== null && c !== false) el.append(c instanceof Node ? c : String(c));
    return el;
  }
  const w = {
    card: (p, kids) => h('section', { class: 'k-card' }, p.title ? h('h3', {}, p.title) : null, p.subtitle ? h('div', { class: 'k-muted' }, p.subtitle) : null, kids),
    row: (p, kids) => h('div', { class: 'k-row' }, kids),
    column: (p, kids) => h('div', { class: 'k-col' }, kids),
    text: (p) => h(p.variant && p.variant.startsWith('h') ? p.variant : 'p', { class: p.variant === 'caption' ? 'k-muted' : '' }, p.text ?? ''),
    metric: (p) => h('div', { class: 'k-metric' }, h('div', { class: 'k-muted' }, p.label), h('b', {}, String(p.value ?? '')), p.delta ? h('small', {}, p.delta) : null),
    table: (p) => h('table', { class: 'k-table' }, h('tr', {}, (p.columns ?? []).map((c) => h('th', {}, c))), (p.rows ?? []).map((r) => h('tr', {}, r.map((v) => h('td', {}, String(v)))))),
    barChart: (p) => {
      const max = Math.max(1, ...(p.values ?? []));
      return h('figure', { class: 'k-chart' }, p.title ? h('figcaption', { class: 'k-muted' }, p.title) : null,
        h('div', { class: 'k-bars' }, (p.labels ?? []).map((l, i) => h('div', { class: 'k-bar' },
          h('span', { class: 'k-fill', style: { height: `${Math.round((100 * (p.values[i] ?? 0)) / max)}%` } }), h('small', {}, l)))));
    },
    alert: (p) => h('div', { class: `k-alert ${p.level ?? 'info'}` }, p.text ?? ''),
    button: (p, onClick) => h('button', { class: `k-btn ${p.variant ?? 'primary'}`, onClick }, p.label ?? 'OK'),
  };
  const registry = {
    Card: (p, kids) => w.card(p, kids), Row: (p, kids) => w.row(p, kids), Column: (p, kids) => w.column(p, kids),
    Text: (p) => w.text(p), Metric: (p) => w.metric(p), Table: (p) => w.table(p), BarChart: (p) => w.barChart(p),
    Alert: (p) => w.alert(p), Divider: () => h('hr'), Badge: (p) => h('span', { class: 'k-badge' }, p.text),
  };

  // ---- 3. a flat element map renderer (declarative mode) ---------------------
  function renderSpec(container, spec, { onAction, custom = {} } = {}) {
    const node = (id, seen = new Set()) => {
      const el = spec.elements?.[id];
      if (!el || seen.has(id)) return h('div', { class: 'k-muted' }, `missing: ${id}`);
      const kids = (el.children ?? []).map((c) => node(c, new Set(seen).add(id)));
      const props = el.props ?? {};
      if (custom[el.type]) return custom[el.type](props, kids, id);
      if (el.type === 'Button') return w.button(props, () => onAction?.(props.action, props.params ?? {}, id));
      const build = registry[el.type];
      return build ? build(props, kids) : h('div', { class: 'k-muted' }, `not in catalog: ${el.type}`);
    };
    container.replaceChildren(node(spec.root));
  }

  // ---- 4. a nested sandbox for model-written HTML (open-ended and mixed) -----
  const CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'";
  const BRIDGE = '<script>(()=>{const l=[];const b={data:undefined,send(n,p){parent.postMessage({genui:1,type:"action",name:n,payload:p??{}},"*")},onData(f){l.push(f);if(b.data!==undefined)f(b.data)}};window.genui=b;addEventListener("message",e=>{if(e.source!==parent||!e.data||e.data.genui!==1)return;if(e.data.type==="data"){b.data=e.data.data;l.forEach(f=>f(b.data))}});const r=()=>parent.postMessage({genui:1,type:"resize",height:document.documentElement.scrollHeight},"*");addEventListener("load",r);new ResizeObserver(r).observe(document.documentElement)})();<\/script>';
  function mountGenerated(container, html, { onAction, height = 240 } = {}) {
    const frame = h('iframe', { sandbox: 'allow-scripts', class: 'k-generated', title: 'generated region' });
    frame.style.height = `${height}px`;
    const head = `<meta http-equiv="Content-Security-Policy" content="${CSP}">${BRIDGE}`;
    frame.srcdoc = /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, (t) => t + head) : head + html;
    let loaded = false;
    let latest;
    frame.addEventListener('load', () => { loaded = true; if (latest !== undefined) frame.contentWindow.postMessage({ genui: 1, type: 'data', data: latest }, '*'); });
    window.addEventListener('message', (event) => {
      if (event.source !== frame.contentWindow || !event.data || event.data.genui !== 1) return;
      if (event.data.type === 'resize') frame.style.height = `${Math.min(900, Math.max(80, event.data.height))}px`;
      if (event.data.type === 'action' && /^[a-z_]{1,40}$/.test(event.data.name)) onAction?.(event.data.name, event.data.payload ?? {});
    });
    container.replaceChildren(frame);
    return { send(data) { latest = data; if (loaded) frame.contentWindow.postMessage({ genui: 1, type: 'data', data }, '*'); } };
  }

  const style = document.createElement('style');
  style.textContent = `
    body{font:14px/1.45 system-ui,sans-serif;margin:0;padding:12px;color:#1d2433;background:var(--host-background,#fff)}
    h2,h3{margin:0 0 6px} p{margin:0} .k-muted{color:#667085;font-size:12px}
    .k-card{border:1px solid #e3e7ee;border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:10px}
    .k-row{display:flex;gap:12px;flex-wrap:wrap}.k-row>*{flex:1 1 0;min-width:0}.k-col{display:flex;flex-direction:column;gap:10px}
    .k-metric{background:#f8fafc;border:1px solid #e3e7ee;border-radius:10px;padding:8px 12px}.k-metric b{font-size:22px;display:block}
    .k-table{border-collapse:collapse;width:100%;font-size:13px}.k-table td,.k-table th{text-align:left;padding:4px 8px;border-bottom:1px solid #e3e7ee}
    .k-bars{display:flex;align-items:flex-end;gap:4px;height:110px}.k-bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%}
    .k-fill{display:block;width:100%;background:#1f6feb;border-radius:4px 4px 0 0;min-height:2px}.k-bar small{font-size:10px;color:#667085}
    .k-btn{font:inherit;border:0;border-radius:8px;padding:7px 14px;cursor:pointer;background:#1f6feb;color:#fff}.k-btn.secondary{background:#e5e7eb;color:#1d2433}
    .k-alert{border-radius:9px;padding:8px 12px;background:#fff7e6;border:1px solid #f5d79a}.k-alert.success{background:#e7f7ef;border-color:#a9dfc3}
    .k-generated{width:100%;border:2px dashed #b39ddb;border-radius:10px;display:block}
    .k-badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;background:#eef0f4}`;
  document.head.append(style);
  window.viewKit = { app, h, w, renderSpec, mountGenerated };
})();
