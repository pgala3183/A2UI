// A minimal MCP Apps host: chat + MCP client + one sandboxed iframe per UI tool call.
//
// The host decides what a view may do. Here it:
//   * mounts the ui:// resource with sandbox="allow-scripts" and a CSP built
//     from the resource's _meta.ui.csp (empty lists = no network at all);
//   * answers ui/initialize with its context, then sends tool-input and
//     tool-result notifications;
//   * proxies tools/call to the same MCP server, shows ui/open-link instead of
//     navigating, feeds ui/message into its own conversation, and records
//     ui/update-model-context for the model's next turn.

import { createShell } from '/common/shell.mjs';
import { h } from '/common/components.mjs';
import { McpClient, PROTOCOL } from '/shared/host/mcp-client.mjs';

const config = await (await fetch('/host/config')).json();
const shell = createShell({ theme: 'MCP Apps', mode: config.mode, title: config.title, prompts: config.prompts, note: config.note });
const mcp = new McpClient('/mcp', (dir, label, payload) => shell.log(dir, label, payload));
const conversation = []; // the host model's conversation, Messages API format
const modelContext = []; // what views asked the host to tell its model
window.host = { mcp, conversation, modelContext, shell };

const textOf = (result) => (result.content ?? []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');

function cspFor(meta) {
  const csp = meta?.ui?.csp ?? {};
  const connect = ['connect-src', ...(csp.connectDomains?.length ? csp.connectDomains : ["'none'"])].join(' ');
  const resources = (csp.resourceDomains ?? []).join(' ');
  return `default-src 'none'; script-src 'unsafe-inline' ${resources}; style-src 'unsafe-inline' ${resources}; img-src data: ${resources}; ${connect}`;
}

class ViewHost {
  constructor(tool, html, meta) {
    this.tool = tool;
    this.frame = h('iframe', { sandbox: 'allow-scripts', class: 'genui-sandbox', title: `${tool.name} view` });
    this.frame.style.height = '200px';
    const csp = `<meta http-equiv="Content-Security-Policy" content="${cspFor(meta)}">`;
    this.frame.srcdoc = /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, (t) => t + csp) : csp + html;
    this.ready = new Promise((resolve) => { this.markReady = resolve; });
    window.addEventListener('message', (event) => this.onMessage(event));
    shell.surface.append(h('div', { class: 'generated-label' }, `${tool._meta.ui.resourceUri} - MCP App view (sandboxed iframe)`), this.frame);
  }

  post(message) { this.frame.contentWindow.postMessage(message, '*'); }
  notify(method, params) { shell.log('out', `bridge ${method}`, params); this.post({ jsonrpc: '2.0', method, params }); }
  respond(id, result) { this.post({ jsonrpc: '2.0', id, result }); }
  fail(id, message) { this.post({ jsonrpc: '2.0', id, error: { code: -32601, message } }); }

  async onMessage(event) {
    if (event.source !== this.frame.contentWindow) return; // only this view
    const msg = event.data;
    if (!msg || msg.jsonrpc !== '2.0' || !msg.method) return;
    if (msg.method !== 'ui/notifications/size-changed') shell.log('in', `bridge ${msg.method}`, msg.params);
    const p = msg.params ?? {};
    switch (msg.method) {
      case 'ui/initialize':
        return this.respond(msg.id, {
          protocolVersion: PROTOCOL,
          hostInfo: { name: 'genux-demo-host', version: '1.0.0' },
          hostCapabilities: { openLinks: {}, serverTools: {}, updateModelContext: {} },
          hostContext: { theme: 'light', displayMode: 'inline', locale: navigator.language },
        });
      case 'ui/notifications/initialized':
        return this.markReady();
      case 'ui/notifications/size-changed':
        this.frame.style.height = `${Math.min(1200, Math.max(80, p.height + 4))}px`;
        return;
      case 'tools/call': // the view calls its own server, through the host
        if (!visibleTo(tools.find((t) => t.name === p.name), 'app')) return this.fail(msg.id, `tool ${p.name} is not available to apps`);
        try {
          return this.respond(msg.id, await mcp.request('tools/call', { name: p.name, arguments: p.arguments ?? {} }));
        } catch (error) {
          return this.fail(msg.id, error.message);
        }
      case 'ui/message': {
        const text = p.content?.text ?? '';
        shell.say('user', `[from the app] ${text}`);
        conversation.push({ role: 'user', content: text });
        this.respond(msg.id, {});
        return hostTurn();
      }
      case 'ui/open-link':
        shell.say('tool', `The app asked to open ${p.url}. This host shows links; it never navigates for an app.`);
        return this.respond(msg.id, {});
      case 'ui/update-model-context':
        modelContext.push(p);
        return this.respond(msg.id, {});
      default:
        return msg.id !== undefined ? this.fail(msg.id, `method not supported: ${msg.method}`) : undefined;
    }
  }
}

async function callTool(tools, block) {
  const tool = tools.find((t) => t.name === block.name);
  const uri = tool?._meta?.ui?.resourceUri;
  let view = null;
  if (uri) {
    const { contents } = await mcp.request('resources/read', { uri });
    const resource = contents[0];
    if (resource.mimeType !== 'text/html;profile=mcp-app') throw new Error(`unexpected mime type ${resource.mimeType}`);
    view = new ViewHost(tool, resource.text, resource._meta);
  }
  const resultPromise = mcp.request('tools/call', { name: block.name, arguments: block.input });
  if (view) {
    await view.ready;
    view.notify('ui/notifications/tool-input', { arguments: block.input });
    view.notify('ui/notifications/tool-result', await resultPromise);
  } else shell.say('tool', textOf(await resultPromise));
  return { type: 'tool_result', tool_use_id: block.id, content: textOf(await resultPromise) };
}

// _meta.ui.visibility: ["model"], ["app"] or both (the default). App-only tools
// (button handlers, say) are hidden from the model; model-only tools from views.
const visibleTo = (tool, who) => Boolean(tool) && (tool._meta?.ui?.visibility ?? ['model', 'app']).includes(who);

let tools = [];
async function hostTurn() {
  // The latest ui/update-model-context rides along with the newest user message.
  const messages = structuredClone(conversation);
  const context = modelContext.at(-1);
  const last = messages.at(-1);
  if (context && last?.role === 'user' && typeof last.content === 'string') {
    last.content = `[app context: ${(context.content ?? []).map((c) => c.text).join(' ')}]\n${last.content}`;
  }
  const response = await fetch('/host/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages, tools: tools.filter((t) => visibleTo(t, 'model')) }) });
  const { content } = await response.json();
  conversation.push({ role: 'assistant', content });
  const results = [];
  for (const block of content) {
    if (block.type === 'text' && block.text) shell.say('assistant', block.text);
    if (block.type === 'tool_use') results.push(await callTool(tools, block));
  }
  if (results.length) conversation.push({ role: 'user', content: results });
  document.body.dataset.turns = String(Number(document.body.dataset.turns ?? 0) + 1);
}

await mcp.initialize();
({ tools } = await mcp.request('tools/list'));
shell.say('tool', `Connected over MCP. Tools: ${tools.map((t) => (t._meta?.ui ? `${t.name} (has UI)` : t.name)).join(', ')}`);
shell.onRun(async (prompt) => {
  shell.say('user', prompt);
  conversation.push({ role: 'user', content: prompt });
  await hostTurn();
});
document.body.dataset.connected = '1';
