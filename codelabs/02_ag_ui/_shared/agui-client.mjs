// A small AG-UI client: the part of @ag-ui/client's HttpAgent these codelabs use.
//
// runAgent() POSTs a RunAgentInput and reads the SSE stream. Each event is
// applied to the agent's local view (messages, tool calls, state) and then
// handed to the page's subscriber. Keeping that bookkeeping here lets each
// codelab's app.mjs focus on what it renders.

import { postSSE } from '/common/sse.mjs';
import { applyPatch } from '/common/jsonpatch.mjs';
import { parsePartial } from '/common/partial-json.mjs';

const uid = (p) => `${p}_${Math.random().toString(36).slice(2, 10)}`;

export class HttpAgent {
  constructor({ url, threadId = uid('thread'), state = {} }) {
    this.url = url;
    this.threadId = threadId;
    this.messages = [];
    this.state = state;
    this.toolCalls = new Map(); // toolCallId -> {id, name, args (text), parsed, done, result}
  }

  addUserMessage(content) {
    this.messages.push({ id: uid('msg'), role: 'user', content });
  }

  addToolResult(toolCallId, content) {
    this.messages.push({ id: uid('msg'), role: 'tool', toolCallId, content: typeof content === 'string' ? content : JSON.stringify(content) });
  }

  async runAgent({ tools = [], context = [], forwardedProps = {} } = {}, onEvent = () => {}) {
    const input = { threadId: this.threadId, runId: uid('run'), state: this.state, messages: this.messages, tools, context, forwardedProps };
    onEvent({ type: '__request', input });
    let assistant = null; // the assistant message being built during this run
    const ensureAssistant = (id) => {
      if (!assistant) {
        assistant = { id: id ?? uid('msg'), role: 'assistant', content: '', toolCalls: [] };
        this.messages.push(assistant);
      }
      return assistant;
    };
    for await (const { data: event } of postSSE(this.url, input)) {
      switch (event.type) {
        case 'TEXT_MESSAGE_START':
          ensureAssistant(event.messageId);
          break;
        case 'TEXT_MESSAGE_CONTENT':
          ensureAssistant(event.messageId).content += event.delta;
          break;
        case 'TOOL_CALL_START': {
          const call = { id: event.toolCallId, name: event.toolCallName, args: '', parsed: undefined, done: false };
          this.toolCalls.set(call.id, call);
          ensureAssistant(event.parentMessageId).toolCalls.push({ id: call.id, type: 'function', function: { name: call.name, arguments: '' } });
          break;
        }
        case 'TOOL_CALL_ARGS': {
          const call = this.toolCalls.get(event.toolCallId);
          call.args += event.delta;
          call.parsed = parsePartial(call.args); // streaming args: usable before they finish
          const entry = assistant?.toolCalls.find((c) => c.id === call.id);
          if (entry) entry.function.arguments = call.args;
          break;
        }
        case 'TOOL_CALL_END': {
          const call = this.toolCalls.get(event.toolCallId);
          call.done = true;
          call.parsed = JSON.parse(call.args || '{}');
          break;
        }
        case 'TOOL_CALL_RESULT': {
          const call = this.toolCalls.get(event.toolCallId);
          if (call) call.result = event.content;
          this.messages.push({ id: event.messageId, role: 'tool', toolCallId: event.toolCallId, content: event.content });
          assistant = null; // text after a tool result belongs to a new assistant message
          break;
        }
        case 'STATE_SNAPSHOT':
          this.state = structuredClone(event.snapshot);
          break;
        case 'STATE_DELTA':
          this.state = applyPatch(this.state, event.delta);
          break;
        case 'MESSAGES_SNAPSHOT':
          this.messages = structuredClone(event.messages);
          break;
        default:
          break;
      }
      onEvent(event);
    }
    return { messages: this.messages, state: this.state };
  }
}

// Short labels for the wire log.
export function describe(event) {
  switch (event.type) {
    case 'TEXT_MESSAGE_CONTENT': return JSON.stringify(event.delta);
    case 'TOOL_CALL_START': return event.toolCallName;
    case 'TOOL_CALL_ARGS': return event.delta;
    case 'TOOL_CALL_RESULT': return event.content;
    case 'STATE_DELTA': return JSON.stringify(event.delta);
    case 'STATE_SNAPSHOT': return JSON.stringify(event.snapshot);
    case 'CUSTOM': return `${event.name} ${JSON.stringify(event.value)}`;
    case 'STEP_STARTED': case 'STEP_FINISHED': return event.stepName;
    case 'RUN_ERROR': return event.message;
    default: return '';
  }
}
