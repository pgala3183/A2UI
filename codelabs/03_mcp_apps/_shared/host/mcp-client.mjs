// A browser MCP client over Streamable HTTP (JSON responses).
// initialize -> the server returns an mcp-session-id header -> every later
// request carries it. Requests have ids; notifications do not.

export const PROTOCOL = '2025-06-18';

export class McpClient {
  constructor(url, log = () => {}) {
    this.url = url;
    this.session = null;
    this.nextId = 0;
    this.log = log;
  }

  async post(body) {
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', 'mcp-protocol-version': PROTOCOL };
    if (this.session) headers['mcp-session-id'] = this.session;
    const response = await fetch(this.url, { method: 'POST', headers, body: JSON.stringify(body) });
    this.session = response.headers.get('mcp-session-id') ?? this.session;
    const text = await response.text();
    if (!text.trim()) return null;
    if ((response.headers.get('content-type') ?? '').includes('text/event-stream')) {
      const data = text.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5)).join('');
      return JSON.parse(data);
    }
    return JSON.parse(text);
  }

  async request(method, params = {}) {
    const id = ++this.nextId;
    this.log('out', `mcp ${method}`, params);
    const reply = await this.post({ jsonrpc: '2.0', id, method, params });
    if (reply.error) {
      this.log('in', `mcp ${method} error`, reply.error);
      throw new Error(reply.error.message);
    }
    this.log('in', `mcp ${method}`, reply.result);
    return reply.result;
  }

  async notify(method, params = {}) {
    await this.post({ jsonrpc: '2.0', method, params });
  }

  async initialize() {
    const result = await this.request('initialize', {
      protocolVersion: PROTOCOL,
      // MCP Apps: the host says it can render text/html;profile=mcp-app resources.
      capabilities: { extensions: { 'io.modelcontextprotocol/ui': { mimeTypes: ['text/html;profile=mcp-app'] } } },
      clientInfo: { name: 'genux-demo-host', version: '1.0.0' },
    });
    await this.notify('notifications/initialized');
    return result;
  }
}
