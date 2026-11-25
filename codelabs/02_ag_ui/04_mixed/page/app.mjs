// AG-UI mixed: state-driven catalog UI + one sandboxed GeneratedView +
// a render tool + a frontend tool that asks the operator before bikes move.
import { setup } from '/shared/page.mjs';
import { ElementView, BASE_REGISTRY } from '/common/elements.mjs';
import { alert, card, button, row, textBlock, h } from '/common/components.mjs';

const { shell, agent, run, ask } = setup({
  mode: 'mixed',
  title: 'State, a generated region, render tools and a human in the loop',
  prompts: ['Build me a rebalancing desk'],
  note: 'Catalog elements arrive as STATE_DELTA. The simulator HTML arrives once as CUSTOM genui.html. show_alert is a render tool. confirm_rebalance is a frontend tool: the page asks you before the backend tool rebalance runs.',
});

// Declared by the page in every RunAgentInput: the agent may call it, the page runs it.
const FRONTEND_TOOLS = [{
  name: 'confirm_rebalance',
  description: 'Ask the operator to confirm a rebalancing plan. Returns {confirmed, plan}.',
  parameters: { type: 'object', properties: { from: { type: 'string' }, to: { type: 'string' }, count: { type: 'integer' } }, required: ['from', 'to', 'count'] },
}];

const artifacts = new Map(); // artifact id -> html (from CUSTOM genui.html)
const registry = {
  ...BASE_REGISTRY,
  GeneratedView: (p, kids, ctx) =>
    ctx.frames.slot(p.artifact, artifacts.get(p.artifact) ?? '<p style="font:13px sans-serif">waiting for the artifact...</p>', {
      label: `GeneratedView "${p.artifact}" - model-written HTML (sandboxed)`, height: p.height ?? 240,
    }),
};
const tools = h('div', { class: 'tool-area' });
const surface = h('div');
shell.surface.append(tools, surface);
const view = new ElementView(surface, { registry, onAction });
const paint = () => view.render(agent.state.ui, agent.state.data);

const pending = new Set();
const handlers = {
  STATE_SNAPSHOT: paint,
  STATE_DELTA: paint,
  CUSTOM(e) {
    if (e.name === 'genui.html') {
      artifacts.set(e.value.artifact, e.value.html);
      paint();
    }
  },
  TOOL_CALL_END(e) {
    const call = agent.toolCalls.get(e.toolCallId);
    if (call.name === 'show_alert') tools.append(alert(call.parsed)); // static: a pre-built component
    if (call.name === 'confirm_rebalance') pending.add(call.id); // frontend tool: answered after the run
  },
  RUN_FINISHED() {
    for (const id of pending) askOperator(agent.toolCalls.get(id));
    pending.clear();
  },
};

function askOperator(call) {
  const { from, to, count } = call.parsed;
  const name = (id) => (agent.state.data?.stations ?? []).find((s) => s.id === id)?.name ?? id;
  const answer = async (confirmed) => {
    box.remove();
    shell.say('user', confirmed ? 'Confirmed.' : 'Cancelled.');
    agent.addToolResult(call.id, { confirmed, plan: call.parsed });
    await go();
  };
  const box = card({ title: 'confirm_rebalance (frontend tool)' }, [
    textBlock({ text: `Move ${count} bikes from ${name(from)} to ${name(to)}?` }),
    row({}, [button({ label: 'Confirm' }, () => answer(true)), button({ label: 'Cancel', variant: 'secondary' }, () => answer(false))]),
  ]);
  box.dataset.confirm = call.id;
  tools.append(box);
}

async function go() {
  await run(handlers, { tools: FRONTEND_TOOLS });
  document.body.dataset.runsDone = String(Number(document.body.dataset.runsDone ?? 0) + 1);
}

async function onAction({ action, params }) {
  const text = `[ui action] ${action} ${JSON.stringify(params ?? {})}`;
  shell.say('user', text);
  agent.addUserMessage(text);
  await go();
}

ask(() => go());
