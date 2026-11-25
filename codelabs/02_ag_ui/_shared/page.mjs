// The AG-UI page loop shared by the four AG-UI codelabs.
//
// setup() builds the shell and an HttpAgent pointed at POST /agent. run()
// starts one AG-UI run: every event is written to the wire log, assistant
// text streams into chat bubbles, and the codelab's own handlers (keyed by
// event type) do the rendering this codelab teaches.

import { createShell } from '/common/shell.mjs';
import { HttpAgent, describe } from '/shared/agui-client.mjs';

export function setup({ mode, title, prompts, note }) {
  const shell = createShell({ theme: 'AG-UI', mode, title, prompts, note });
  const agent = new HttpAgent({ url: '/agent' });
  const bubbles = new Map();
  window.agui = { agent, shell };

  async function run(handlers = {}, options = {}) {
    await agent.runAgent(options, (event) => {
      if (event.type === '__request') {
        const i = event.input;
        shell.log('out', 'RunAgentInput', {
          threadId: i.threadId, runId: i.runId, messages: i.messages.length,
          state: Object.keys(i.state ?? {}), tools: (i.tools ?? []).map((t) => t.name),
        });
        return;
      }
      shell.log('in', event.type, describe(event));
      if (event.type === 'TEXT_MESSAGE_START') bubbles.set(event.messageId, shell.say('assistant'));
      if (event.type === 'TEXT_MESSAGE_CONTENT') {
        const bubble = bubbles.get(event.messageId) ?? shell.say('assistant');
        bubbles.set(event.messageId, bubble);
        bubble.textContent += event.delta;
      }
      handlers[event.type]?.(event);
      handlers.any?.(event);
    });
  }

  function ask(onPrompt) {
    shell.onRun(async (prompt) => {
      shell.say('user', prompt);
      agent.addUserMessage(prompt);
      await onPrompt(prompt);
    });
  }

  return { shell, agent, run, ask, bubbles };
}
