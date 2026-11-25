// Parse JSON that is still arriving: '{"name": "Mar' -> {name: "Mar"}.
//
// Streaming UIs render tool arguments and specs before the model finishes.
// The parser closes the open string, drops a dangling key or comma, closes
// every open bracket, and parses what is left. It returns undefined when
// nothing useful has arrived yet.

export function completeJSON(text) {
  const stack = [];
  let inString = false;
  let escaped = false;
  let lastSafe = 0; // end of the last position where cutting is safe
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (c === '\\') escaped = true;
      else if (c === '"') inString = false;
      continue;
    }
    if (c === '"') inString = true;
    else if (c === '{' || c === '[') stack.push(c === '{' ? '}' : ']');
    else if (c === '}' || c === ']') stack.pop();
    if (c === ',' || c === '{' || c === '[') lastSafe = i + 1;
  }
  let body = text;
  if (inString) body += escaped ? '\\"' : '"';
  return { body, closers: stack.slice().reverse().join(''), lastSafe };
}

function attempt(text) {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch {
    return { ok: false };
  }
}

export function parsePartial(text) {
  if (!text || !text.trim()) return undefined;
  const whole = attempt(text);
  if (whole.ok) return whole.value;
  // 1) close the open string and brackets as they are
  let { body, closers, lastSafe } = completeJSON(text);
  let result = attempt(body.replace(/[,:\s]+$/, '') + closers);
  if (result.ok) return result.value;
  // 2) a key without a value: '{"a": 1, "b' or '{"a": 1, "b":' -> drop it
  result = attempt(body.replace(/,?\s*"[^"]*"\s*:?\s*$/, '') + closers);
  if (result.ok) return result.value;
  // 3) cut back to the last comma or opening bracket and close from there
  const cut = text.slice(0, lastSafe).replace(/,\s*$/, '');
  ({ body, closers } = completeJSON(cut));
  result = attempt(body + closers);
  return result.ok ? result.value : undefined;
}
