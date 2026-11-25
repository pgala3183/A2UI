// The A2UI page loop, shared by the four A2UI codelabs.
//
//   POST /run {prompt}      -> SSE: one A2UI envelope per `data:` frame,
//                              plus `event: text` frames with the model's prose
//   POST /action {action}   -> SSE: the server's answer, also A2UI envelopes
//
// Transport is deliberately boring: A2UI does not care how its messages
// travel (A2A, AG-UI, WebSocket, SSE). Theme 02 carries UI over AG-UI.

import { createShell } from '/common/shell.mjs';
import { postSSE } from '/common/sse.mjs';
import { Processor, messageKind } from '/shared/surface.mjs';
import { SurfaceView } from '/shared/render.mjs';

export function startA2uiApp({ mode, title, prompts, note, custom = {} }) {
  const shell = createShell({ theme: 'A2UI', mode, title, prompts, note });
  const processor = new Processor();
  const views = new Map(); // surfaceId -> SurfaceView
  window.a2ui = { processor, views, shell }; // for the demo script and the browser console

  function paint(kind, surfaceId) {
    if (kind === 'deleteSurface') {
      views.get(surfaceId)?.container.remove();
      views.delete(surfaceId);
      return;
    }
    let view = views.get(surfaceId);
    if (!view) {
      const container = document.createElement('div');
      container.className = 'a2ui-surface';
      container.dataset.surface = surfaceId;
      shell.surface.append(container);
      view = new SurfaceView(processor.surfaces.get(surfaceId), container, { onAction, custom });
      views.set(surfaceId, view);
    }
    view.render();
  }

  async function stream(url, body) {
    let bubble = null;
    for await (const { event, data } of postSSE(url, body)) {
      if (event === 'text') {
        bubble ??= shell.say('assistant');
        bubble.textContent += data.text;
        continue;
      }
      if (event === 'note' || event === 'error') {
        shell.log('note', event, data);
        continue;
      }
      const kind = messageKind(data);
      shell.log('in', kind ?? 'unknown', data);
      if (!kind) continue;
      const { surfaceId } = processor.process(data);
      paint(kind, surfaceId);
    }
  }

  async function onAction(envelope) {
    shell.log('out', `action: ${envelope.action.name}`, envelope);
    await stream('/action', envelope);
  }

  shell.onRun(async (prompt) => {
    shell.say('user', prompt);
    await stream('/run', { prompt });
  });
  return { shell, processor, views };
}
