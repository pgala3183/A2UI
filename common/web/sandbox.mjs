// Mount model-written HTML in a sandboxed iframe.
//
// Three rules keep the generated document away from the page:
//   1. sandbox="allow-scripts" and NOT allow-same-origin: the frame gets an
//      opaque origin, so it cannot read the page, its cookies or storage.
//   2. A Content-Security-Policy <meta> is injected first in <head>: no network,
//      no external scripts, inline code only.
//   3. The page accepts messages only from this frame's window and only in one
//      shape: {genui: 1, type: 'action' | 'resize', ...}. Everything else is dropped.
//
// The injected bridge gives the document two calls: genui.send(name, payload)
// and genui.onData(callback). Each codelab maps them onto its own protocol.

export const CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; " +
  "img-src data:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'";

export const BRIDGE = `<script>
(() => {
  const listeners = [];
  const bridge = {
    data: undefined,
    send(name, payload) { parent.postMessage({ genui: 1, type: 'action', name, payload: payload ?? {} }, '*'); },
    onData(fn) { listeners.push(fn); if (bridge.data !== undefined) fn(bridge.data); },
  };
  window.genui = bridge;
  addEventListener('message', (event) => {
    if (event.source !== parent || !event.data || event.data.genui !== 1) return;
    if (event.data.type === 'data') { bridge.data = event.data.data; listeners.forEach((fn) => fn(bridge.data)); }
  });
  const report = () => parent.postMessage({ genui: 1, type: 'resize', height: document.documentElement.scrollHeight }, '*');
  addEventListener('load', report);
  new ResizeObserver(report).observe(document.documentElement);
})();
<\/script>`;

// Insert the CSP meta tag and the bridge as the first children of <head>.
export function prepare(html, { csp = CSP } = {}) {
  const head = `<meta http-equiv="Content-Security-Policy" content="${csp}">${BRIDGE}`;
  if (/<head[^>]*>/i.test(html)) return html.replace(/<head[^>]*>/i, (tag) => tag + head);
  if (/<html[^>]*>/i.test(html)) return html.replace(/<html[^>]*>/i, (tag) => `${tag}<head>${head}</head>`);
  return `<!doctype html><html><head>${head}</head><body>${html}</body></html>`;
}

const ACTION_NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,48}$/;

export function cleanPayload(payload) {
  try {
    const text = JSON.stringify(payload ?? {});
    return text.length > 10000 ? { error: 'payload too large' } : JSON.parse(text);
  } catch {
    return {};
  }
}

export function mountSandbox(container, html, { onAction, title = 'generated view', height = 280 } = {}) {
  const frame = document.createElement('iframe');
  frame.setAttribute('sandbox', 'allow-scripts');
  frame.setAttribute('title', title);
  frame.className = 'genui-sandbox';
  frame.style.height = `${height}px`;
  let loaded = false;
  let pending;
  const post = (data) => frame.contentWindow?.postMessage({ genui: 1, type: 'data', data }, '*');
  frame.addEventListener('load', () => {
    loaded = true;
    if (pending !== undefined) post(pending);
  });
  const onMessage = (event) => {
    if (event.source !== frame.contentWindow) return; // only messages from this frame
    const message = event.data;
    if (!message || message.genui !== 1) return; // only the bridge's shape
    if (message.type === 'resize' && Number.isFinite(message.height)) {
      frame.style.height = `${Math.min(Math.max(message.height, 60), 1400)}px`;
    } else if (message.type === 'action' && ACTION_NAME.test(message.name)) {
      onAction?.(message.name, cleanPayload(message.payload));
    }
  };
  window.addEventListener('message', onMessage);
  frame.srcdoc = prepare(html);
  container.replaceChildren(frame);
  return {
    frame,
    send(data) {
      pending = data;
      if (loaded) post(data);
    },
    destroy() {
      window.removeEventListener('message', onMessage);
      frame.remove();
    },
  };
}
