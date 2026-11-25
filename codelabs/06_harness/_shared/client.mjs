// The harness's web surface, shared by the four harness codelabs.
// It draws the same events the terminal surface draws:
//   text / tool_call / tool_result           the transcript
//   ui {kind: component|spec|html|data}       generative UI, one slot per view id
//   permission_request                        an Approve / Deny card -> POST /approve
// Clicks inside generated UI go to POST /ui-action; the harness accepts only
// actions the view declared when it was rendered.

import { createShell } from '/common/shell.mjs';
import { postSSE } from '/common/sse.mjs';
import * as w from '/common/components.mjs';
import { ElementView, BASE_REGISTRY } from '/common/elements.mjs';
import { mountSandbox } from '/common/sandbox.mjs';

export async function startHarnessApp({ mode, title, prompts, note }) {
  const shell = createShell({ theme: 'Harness', mode, title, prompts, note });
  await fetch('/reset', { method: 'POST' });
  const slots = new Map(); // view id -> { el, spec?, mount? }
  const artifacts = new Map(); // view id -> html, for GeneratedView elements inside specs
  window.harness = { slots, shell };

  const slot = (view) => {
    if (!slots.has(view)) {
      const el = w.h('div', { class: 'view', dataset: { view } });
      shell.surface.append(el);
      slots.set(view, { el });
    }
    return slots.get(view);
  };

  const registry = {
    ...BASE_REGISTRY,
    GeneratedView: (p, kids, ctx) => ctx.frames.slot(p.artifact, artifacts.get(p.artifact) ?? '<p style="font:13px sans-serif">waiting for the generated view...</p>',
      { label: `GeneratedView "${p.artifact}" - model-written HTML (sandboxed)`, height: p.height ?? 240 }),
  };

  function renderUi(e) {
    if (e.kind === 'component') {
      const build = registry[e.component] ?? ((p) => w.alert({ text: `unknown component ${e.component}` }));
      slot(e.view).el.replaceChildren(build(e.props, [], { act: () => {} }));
    } else if (e.kind === 'spec') {
      const s = slot(e.view);
      s.spec ??= new ElementView(s.el, {
        registry,
        onAction: ({ source, element, action, params }) => uiAction(source === 'frame' ? element : e.view, action, params),
      });
      s.spec.render(e.spec);
    } else if (e.kind === 'html') {
      artifacts.set(e.view, e.html);
      if (e.placement === 'embedded') { // a GeneratedView inside a spec shows it
        for (const s of slots.values()) if (s.spec?.spec) s.spec.render(s.spec.spec);
        return;
      }
      const s = slot(e.view);
      s.el.replaceChildren(w.h('div', { class: 'generated-label' }, `${e.title} - model-written HTML (sandboxed iframe)`), w.h('div'));
      s.mount = mountSandbox(s.el.lastChild, e.html, { onAction: (name, payload) => uiAction(e.view, name, payload), height: 300 });
    } else if (e.kind === 'data') {
      slots.get(e.view)?.mount?.send(e.data);
      for (const s of slots.values()) s.spec?.frames.send(e.data, e.view);
    }
  }

  function askPermission(e) {
    const box = w.card({ title: 'Permission needed' }, [
      w.textBlock({ text: `${e.name} ${JSON.stringify(e.input).slice(0, 240)}...` }),
      w.row({}, [
        w.button({ label: 'Approve' }, () => decide(true)),
        w.button({ label: 'Deny', variant: 'secondary' }, () => decide(false)),
      ]),
    ]);
    box.dataset.permission = e.id;
    shell.chat.append(box);
    async function decide(approve) {
      box.remove();
      shell.say('user', approve ? `Approved ${e.name}.` : `Denied ${e.name}.`);
      await stream('/approve', { id: e.id, approve });
    }
  }

  async function stream(url, body) {
    let bubble = null;
    for await (const { data: e } of postSSE(url, body)) {
      shell.log('in', e.type === 'ui' ? `ui ${e.kind}` : e.type, e.type === 'text' ? e.text : e.name ?? e.view ?? e.reason ?? e.message);
      if (e.type === 'text') {
        bubble ??= shell.say('assistant');
        bubble.textContent += e.text;
        continue;
      }
      bubble = null;
      if (e.type === 'tool_call') shell.say('tool', `-> ${e.name}(${JSON.stringify(e.input).slice(0, 110)})`);
      else if (e.type === 'tool_result') shell.say('tool', `<- ${e.content.slice(0, 140)}`).style.color = e.is_error ? '#a12622' : '';
      else if (e.type === 'ui') renderUi(e);
      else if (e.type === 'permission_request') askPermission(e);
      else if (e.type === 'error') shell.say('tool', `! ${e.message}`);
    }
    document.body.dataset.streams = String(Number(document.body.dataset.streams ?? 0) + 1);
  }

  async function uiAction(view, action, params) {
    shell.say('user', `[ui action] ${action} ${JSON.stringify(params)}`);
    shell.log('out', 'ui-action', { view, action, params });
    await stream('/ui-action', { view, action, params });
  }

  shell.onRun(async (prompt) => {
    shell.say('user', prompt);
    await stream('/run', { prompt });
  });
}
