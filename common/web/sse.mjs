// Read a Server-Sent Events stream from a POST request.
// EventSource only does GET, and every codelab POSTs a JSON body (the prompt,
// an AG-UI RunAgentInput, an action), so this reads the stream with fetch.

export function parseFrame(frame) {
  let event = null;
  const data = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
  }
  if (!data.length) return null;
  const raw = data.join('\n');
  try {
    return { event, data: JSON.parse(raw) };
  } catch {
    return { event, data: raw };
  }
}

// Split any text into complete frames; returns [frames, rest].
export function splitFrames(buffer) {
  const frames = [];
  buffer = buffer.replace(/\r\n/g, '\n');
  let index;
  while ((index = buffer.indexOf('\n\n')) >= 0) {
    frames.push(buffer.slice(0, index));
    buffer = buffer.slice(index + 2);
  }
  return [frames, buffer];
}

export async function* postSSE(url, body, { signal } = {}) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body ?? {}),
    signal,
  });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    let frames;
    [frames, buffer] = splitFrames(buffer + value);
    for (const frame of frames) {
      const parsed = parseFrame(frame);
      if (parsed) yield parsed;
    }
  }
}

export async function postJSON(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  return response.json();
}
