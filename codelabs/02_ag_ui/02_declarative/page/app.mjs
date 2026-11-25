// AG-UI declarative: the page renders agent.state.ui after every state event.
// A button click starts a new run that carries the current state back.
import { setup } from '/shared/page.mjs';
import { ElementView } from '/common/elements.mjs';

const { shell, agent, run, ask } = setup({
  mode: 'declarative',
  title: 'The UI is shared state',
  prompts: ['Build me a dashboard for the whole network'],
  note: 'The model writes catalog elements; the server turns each into a STATE_DELTA (JSON Patch). Click a button: the next run sends the state back and only the changed elements are patched.',
});

const view = new ElementView(shell.surface, { onAction });
const paint = () => view.render(agent.state.ui);
const handlers = { STATE_SNAPSHOT: paint, STATE_DELTA: paint };

async function onAction({ action, params }) {
  const text = `[ui action] ${action} ${JSON.stringify(params ?? {})}`;
  shell.say('user', text);
  agent.addUserMessage(text);
  await run(handlers);
  document.body.dataset.actions = String(Number(document.body.dataset.actions ?? 0) + 1);
}

ask(() => run(handlers));
