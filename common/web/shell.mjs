// The page frame every codelab shares: a header, a prompt bar, the rendered
// surface on the left and a "wire" log on the right that lists every message
// that crossed the network. Keeping the frame identical lets each codelab's
// app.mjs contain only the protocol it teaches.

import { h } from './components.mjs';

export function createShell({ theme, mode, title, prompts = [], note } = {}) {
  const input = h('input', { class: 'prompt-input', value: prompts[0] ?? '', 'aria-label': 'prompt' });
  const run = h('button', { class: 'w-button primary', id: 'run' }, 'Run');
  const status = h('span', { class: 'status', id: 'status' }, 'idle');
  const chips = prompts.slice(1).map((p) => h('button', { class: 'chip', onClick: () => { input.value = p; } }, p));
  const chat = h('div', { class: 'chat', id: 'chat' });
  const surface = h('div', { class: 'surface', id: 'surface' });
  const log = h('ol', { class: 'wire', id: 'wire' });
  const count = h('span', { class: 'wire-count' }, '0');

  const parts = [
    h('header', { class: 'top' },
      h('span', { class: 'theme' }, theme),
      h('h1', {}, title),
      h('span', { class: `mode mode-${mode}` }, mode)),
    note ? h('p', { class: 'note' }, note) : null,
    h('div', { class: 'prompt-bar' }, input, run, status),
    chips.length ? h('div', { class: 'chips' }, chips) : null,
    h('main', { class: 'layout' },
      h('section', { class: 'stage' }, chat, surface),
      h('aside', { class: 'wire-panel' }, h('h2', {}, 'Wire ', count), log)),
  ];
  document.body.append(...parts.filter(Boolean)); // append(null) would print "null"

  let n = 0;
  const shell = {
    surface,
    chat,
    input,
    setStatus(text) {
      status.textContent = text;
    },
    // dir: 'in' (server -> page), 'out' (page -> server), 'note'
    log(dir, label, payload) {
      n += 1;
      count.textContent = String(n);
      const body = payload === undefined ? '' : typeof payload === 'string' ? payload : JSON.stringify(payload);
      const item = h('li', { class: `wire-item ${dir}`, dataset: { label } },
        h('span', { class: 'dir' }, dir === 'in' ? '<-' : dir === 'out' ? '->' : '--'),
        h('b', {}, label),
        body ? h('code', {}, body.length > 220 ? `${body.slice(0, 217)}...` : body) : null);
      log.append(item);
      log.scrollTop = log.scrollHeight;
      return item;
    },
    say(role, text = '') {
      const bubble = h('div', { class: `bubble ${role}` }, text);
      chat.append(bubble);
      return bubble;
    },
    clear() {
      chat.replaceChildren();
      surface.replaceChildren();
    },
    onRun(fn) {
      const go = async () => {
        run.disabled = true;
        shell.setStatus('running...');
        const started = performance.now();
        try {
          await fn(input.value);
          shell.setStatus(`done in ${Math.round(performance.now() - started)} ms`);
        } catch (error) {
          shell.setStatus(`error: ${error.message}`);
          shell.log('note', 'error', error.message);
        } finally {
          run.disabled = false;
          document.body.dataset.runs = String(Number(document.body.dataset.runs ?? 0) + 1);
        }
      };
      run.addEventListener('click', go);
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
      return go;
    },
  };
  return shell;
}
