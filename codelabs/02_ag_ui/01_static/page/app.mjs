// AG-UI static: a registry maps tool names to pre-built components.
// The page renders a tool call while its arguments are still streaming.
import { setup } from '/shared/page.mjs';
import { stationCard, alert, h } from '/common/components.mjs';

const { shell, agent, run, ask } = setup({
  mode: 'static',
  title: 'Tool calls are components',
  prompts: ['How is Market St doing?', 'How is the Ferry Building doing?', 'How is Caltrain Depot doing?'],
  note: 'The model calls show_station_card / show_alert; the page owns those components and draws them from the streamed arguments. get_station is a backend tool.',
});

// The whole "catalog" of static generative UI: tool name -> component.
const registry = {
  show_station_card: (args) => stationCard(args),
  show_alert: (args) => alert({ level: args.level, text: args.text ?? '' }),
};

const slots = new Map(); // toolCallId -> element on the page

function draw(id) {
  const call = agent.toolCalls.get(id);
  const slot = slots.get(id);
  if (!call || !slot) return;
  slot.replaceChildren(registry[call.name](call.parsed ?? {}));
  slot.dataset.done = String(call.done);
}

const handlers = {
  TOOL_CALL_START(e) {
    if (registry[e.toolCallName]) {
      const slot = h('div', { class: 'tool-ui', dataset: { tool: e.toolCallName } });
      slots.set(e.toolCallId, slot);
      shell.surface.append(slot);
    } else {
      shell.say('tool', `calling ${e.toolCallName}(...)`).dataset.call = e.toolCallId;
    }
  },
  TOOL_CALL_ARGS: (e) => draw(e.toolCallId), // progressive: partial JSON -> partial card
  TOOL_CALL_END: (e) => draw(e.toolCallId),
  TOOL_CALL_RESULT(e) {
    const bubble = document.querySelector(`[data-call="${e.toolCallId}"]`);
    if (bubble) bubble.textContent += ` -> ${e.content.slice(0, 120)}`;
  },
};

ask(() => run(handlers));
