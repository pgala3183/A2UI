// The OpenUI Lang page loop shared by the four OpenUI codelabs.
//
//   GET  /library                 the component library (names + parameter order)
//   POST /run {prompt}            SSE: `line` (a validated statement), `pending`
//                                 (progress of a long line), `refused`, `note`
//   POST /action {action, ...}    SSE: more `line` events; a statement with an
//                                 existing id replaces it (incremental update)

import { createShell } from '/common/shell.mjs';
import { postSSE } from '/common/sse.mjs';
import { morph, FrameHost } from '/common/morph.mjs';
import { h } from '/common/components.mjs';
import { Program, resolve } from '/shared/openui-parse.mjs';
import { renderNode } from '/shared/render.mjs';

export async function startOpenUiApp({ mode, title, prompts, note }) {
  const library = await (await fetch('/library')).json();
  const shell = createShell({ theme: 'OpenUI Lang', mode, title, prompts, note });
  const view = h('div', { class: 'openui-view' });
  const source = h('pre', { class: 'source', id: 'program' });
  shell.surface.append(view, h('details', { open: true }, h('summary', {}, 'Program (accepted statements)'), source));

  let program = new Program();
  const pending = new Map(); // statement id -> {component, chars} while its line streams
  const tabs = new Map();
  const sources = new Map(); // statement id -> its latest line, for the program panel
  const timing = { start: 0, firstPaint: null, lines: 0 };
  const frames = new FrameHost({ onAction: (key, name, payload) => onAction(name, payload, key) });
  window.openui = { program: () => program, timing, library };

  function paint() {
    const frameData = new Map();
    const ctx = { pending, tabs, frames, frameData, act: (action, params) => onAction(action, params, 'button'), setTab: (id, t) => { tabs.set(id, t); paint(); } };
    morph(view, [renderNode(resolve(program, library), ctx)]);
    frames.attach(view);
    for (const [key, data] of frameData) frames.send(data, key);
  }

  async function stream(url, body) {
    timing.start = performance.now();
    timing.firstPaint = null;
    let bubble = null;
    for await (const { event, data } of postSSE(url, body)) {
      if (event === 'line') {
        const id = program.add(data.line); // same id again = replace
        pending.delete(id);
        timing.lines += 1;
        shell.log('in', `${id} =`, data.line.slice(id.length + 3));
        sources.set(id, data.line);
        source.textContent = [...sources.values()].join('\n');
        paint();
        if (timing.firstPaint === null && program.statements.has('root')) {
          timing.firstPaint = Math.round(performance.now() - timing.start);
          shell.log('note', 'first paint', `${timing.firstPaint} ms`);
        }
      } else if (event === 'pending') {
        pending.set(data.id, data);
        paint();
      } else if (event === 'text') {
        bubble ??= shell.say('assistant');
        bubble.textContent += data.text;
      } else {
        shell.log('note', event ?? 'message', data);
      }
    }
  }

  async function onAction(action, params, sourceId) {
    const body = { action, params, source: sourceId };
    shell.log('out', `action ${action}`, body);
    await stream('/action', body);
    document.body.dataset.actions = String(Number(document.body.dataset.actions ?? 0) + 1);
  }

  shell.onRun(async (prompt) => {
    shell.say('user', prompt);
    program = new Program();
    sources.clear();
    pending.clear();
    await stream('/run', { prompt });
  });
  return { shell };
}
