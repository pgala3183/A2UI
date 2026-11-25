// The json-render page loop shared by the four json-render codelabs.
//
//   POST /run {prompt}                     -> SSE `event: patch` frames (validated ops)
//   POST /action {action, params, state}   -> SSE patches answering the action
//
// Every patch is applied to the spec and the spec is re-rendered, so the
// page paints as soon as the root element exists ("first paint").

import { createShell } from '/common/shell.mjs';
import { postSSE } from '/common/sse.mjs';
import { applyOp } from '/common/jsonpatch.mjs';
import { SpecView } from '/shared/spec.mjs';
import { registry } from '/shared/registry.mjs';

export function startJsonRenderApp({ mode, title, prompts, note }) {
  const shell = createShell({ theme: 'json-render', mode, title, prompts, note });
  const view = new SpecView(shell.surface, { registry, onAction });
  const timing = { start: 0, firstPaint: null, done: null, patches: 0 };
  window.jr = { view, shell, timing };

  async function stream(url, body) {
    timing.start = performance.now();
    timing.firstPaint = null;
    timing.patches = 0;
    let bubble = null;
    for await (const { event, data } of postSSE(url, body)) {
      if (event === 'patch') {
        view.spec = applyOp(view.spec, data);
        timing.patches += 1;
        shell.log('in', `${data.op} ${data.path}`, data.value);
        view.render();
        if (timing.firstPaint === null && view.spec.root && view.spec.elements[view.spec.root]) {
          timing.firstPaint = Math.round(performance.now() - timing.start);
          shell.log('note', 'first paint', `${timing.firstPaint} ms after the request, patch #${timing.patches}`);
        }
      } else if (event === 'text') {
        bubble ??= shell.say('assistant');
        bubble.textContent += data.text;
      } else {
        shell.log('note', event ?? 'message', data);
      }
    }
    timing.done = Math.round(performance.now() - timing.start);
  }

  async function onAction({ action, params, element }) {
    const body = { action, params, element, state: view.spec.state };
    shell.log('out', `action ${action}`, body);
    await stream('/action', body);
    document.body.dataset.actions = String(Number(document.body.dataset.actions ?? 0) + 1);
  }

  shell.onRun(async (prompt) => {
    shell.say('user', prompt);
    view.spec = { root: null, elements: {}, state: {} };
    await stream('/run', { prompt });
  });
  return { shell, view };
}
