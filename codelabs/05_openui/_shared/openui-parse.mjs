// OpenUI Lang parser, the browser twin of openui_parse.py.
// One statement per line: id = Expression. Capitalised calls are components,
// lowercase names are (possibly forward) references, literals are JSON.

const TOKEN = /\s*(?:("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|([()[\]{},:=]))/y;
const HEAD = /^\s*([a-z_][A-Za-z0-9_]*)\s*=\s*([A-Z][A-Za-z0-9_]*)?/;

export function tokenize(line) {
  const tokens = [];
  const text = line.trimEnd();
  TOKEN.lastIndex = 0;
  while (TOKEN.lastIndex < text.length) {
    const at = TOKEN.lastIndex;
    const m = TOKEN.exec(text);
    if (!m || TOKEN.lastIndex === at) throw new Error(`unexpected character at ${at}: ${text.slice(at, at + 12)}`);
    if (m[1] !== undefined) tokens.push(['str', JSON.parse(m[1])]);
    else if (m[2] !== undefined) tokens.push(['num', Number(m[2])]);
    else if (m[3] !== undefined) tokens.push(['name', m[3]]);
    else tokens.push(['punct', m[4]]);
  }
  return tokens;
}

function reader(tokens) {
  let i = 0;
  const peek = () => tokens[i] ?? [null, null];
  const take = (value) => {
    const [kind, text] = peek();
    if (kind === null || (value !== undefined && text !== value)) throw new Error(`expected ${value ?? 'a value'}, got ${text}`);
    i += 1;
    return [kind, text];
  };
  const items = (close) => {
    const out = [];
    while (peek()[1] !== close) {
      out.push(expr());
      if (peek()[1] === ',') take(',');
      else if (peek()[1] !== close) throw new Error(`expected ',' or '${close}'`);
    }
    take(close);
    return out;
  };
  function expr() {
    const [kind, text] = take();
    if (kind === 'str' || kind === 'num') return ['lit', text];
    if (kind === 'punct' && text === '[') return ['list', items(']')];
    if (kind === 'punct' && text === '{') {
      const members = {};
      while (peek()[1] !== '}') {
        const [keyKind, key] = take();
        if (keyKind !== 'str' && keyKind !== 'name') throw new Error(`bad object key ${key}`);
        take(':');
        members[key] = expr();
        if (peek()[1] === ',') take(',');
      }
      take('}');
      return ['obj', members];
    }
    if (kind === 'name') {
      if (text === 'true' || text === 'false' || text === 'null') return ['lit', { true: true, false: false, null: null }[text]];
      if (peek()[1] === '(') {
        take('(');
        return ['call', text, items(')')];
      }
      return ['ref', text];
    }
    throw new Error(`unexpected ${text}`);
  }
  return { expr, peek, take };
}

export function parseStatement(line) {
  const r = reader(tokenize(line));
  const [kind, name] = r.take();
  if (kind !== 'name' || !/^[a-z_]/.test(name)) throw new Error('a statement starts with a lowercase id');
  r.take('=');
  const value = r.expr();
  if (r.peek()[0] !== null) throw new Error(`unexpected ${r.peek()[1]} after the expression`);
  return [name, value];
}

export class Program {
  constructor() {
    this.statements = new Map();
    this.buffer = '';
  }

  // Streamed text in; complete lines out. The unfinished line waits in buffer.
  feed(chunk) {
    this.buffer += chunk;
    const done = [];
    let index;
    while ((index = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, index).trim();
      this.buffer = this.buffer.slice(index + 1);
      if (line && !/^(```|#|\/\/)/.test(line)) done.push(line);
    }
    return done;
  }

  add(line) {
    const [id, value] = parseStatement(line);
    this.statements.set(id, value); // a later statement with the same id wins
    return id;
  }

  pending() {
    const m = HEAD.exec(this.buffer);
    return m ? { id: m[1], component: m[2] ?? null, chars: this.buffer.length } : null;
  }
}

// Statements -> {type, id, props} tree. library: {Name: {params: [{name}]}}
export function resolve(program, library, root = 'root') {
  const value = (node, path, seen) => {
    const [kind] = node;
    if (kind === 'lit') return node[1];
    if (kind === 'list') return node[1].map((n, i) => value(n, `${path}.${i}`, seen));
    if (kind === 'obj') return Object.fromEntries(Object.entries(node[1]).map(([k, v]) => [k, value(v, `${path}.${k}`, seen)]));
    if (kind === 'ref') {
      const name = node[1];
      if (seen.has(name)) return { type: '__cycle', id: name };
      if (!program.statements.has(name)) return { type: '__missing', id: name };
      return value(program.statements.get(name), name, new Set(seen).add(name));
    }
    const [, name, args] = node;
    const params = (library[name]?.params ?? []).map((p) => p.name);
    const props = {};
    args.forEach((a, i) => { props[params[i] ?? `arg${i}`] = value(a, `${path}.${i}`, seen); });
    return { type: name, id: path, props };
  };
  if (!program.statements.has(root)) return { type: '__missing', id: root };
  return value(program.statements.get(root), root, new Set([root]));
}
