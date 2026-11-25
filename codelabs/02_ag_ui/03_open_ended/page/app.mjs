// AG-UI open-ended: prose in the chat, the HTML source streaming beside it,
// and the finished document mounted in a sandbox when CUSTOM genui.html arrives.
import { setup } from '/shared/page.mjs';
import { mountSandbox } from '/common/sandbox.mjs';
import { h } from '/common/components.mjs';

const { shell, agent, run, ask, bubbles } = setup({
  mode: 'open-ended',
  title: 'HTML streamed over AG-UI',
  prompts: ['Give me an interactive trip-cost calculator'],
  note: 'The model writes a whole HTML document inside its text reply. The page shows the source as it streams; the agent sends the checked document as a CUSTOM event and the page mounts it in a sandboxed iframe.',
});

const mounts = new Map(); // artifact id -> sandbox mount
const sources = new Map(); // messageId -> <pre> with the streaming source

// Split a reply into prose and the html block (which may still be open).
function split(text) {
  const start = text.indexOf('```html');
  if (start < 0) return { prose: text, code: null };
  const rest = text.slice(start + 7).replace(/^\s*\n/, '');
  const end = rest.indexOf('```');
  const code = end < 0 ? rest : rest.slice(0, end);
  const after = end < 0 ? '' : rest.slice(end + 3);
  return { prose: `${text.slice(0, start)}[HTML document: ${code.length} chars]${after}`, code };
}

const handlers = {
  TEXT_MESSAGE_CONTENT(e) {
    const message = agent.messages.find((m) => m.id === e.messageId);
    const { prose, code } = split(message?.content ?? '');
    bubbles.get(e.messageId).textContent = prose;
    if (code !== null) {
      if (!sources.has(e.messageId)) {
        const pre = h('pre', { class: 'source' });
        sources.set(e.messageId, pre);
        bubbles.get(e.messageId).after(pre);
      }
      const pre = sources.get(e.messageId);
      pre.textContent = code;
      pre.scrollTop = pre.scrollHeight;
    }
  },
  CUSTOM(e) {
    if (e.name === 'genui.html') {
      const slot = h('div', { class: 'artifact', dataset: { artifact: e.value.artifact } });
      shell.surface.append(h('div', { class: 'generated-label' }, `${e.value.title} - model-written HTML (sandboxed)`), slot);
      mounts.set(e.value.artifact, mountSandbox(slot, e.value.html, { onAction, height: 300 }));
      agent.state = { ...agent.state, artifact: e.value.artifact }; // sent back on the next run
    } else if (e.name === 'genui.data') {
      mounts.get(e.value.artifact)?.send(e.value.data);
    } else if (e.name === 'genui.html.rejected') {
      shell.say('tool', `document rejected: ${e.value.problems.join('; ')}`);
    }
  },
};

async function onAction(name, payload) {
  const text = `[ui action] ${name} ${JSON.stringify(payload)}`;
  shell.say('user', text);
  agent.addUserMessage(text);
  await run(handlers);
  document.body.dataset.actions = String(Number(document.body.dataset.actions ?? 0) + 1);
}

ask(() => run(handlers));
