// Harness open-ended: render_html asks for permission, then mounts in a sandbox.
import { startHarnessApp } from '/shared/client.mjs';

await startHarnessApp({
  mode: 'open-ended',
  title: 'render_html behind a permission gate',
  prompts: ['Make me an interactive trip-cost calculator'],
  note: 'render_html has permission "ask": the loop pauses until you approve. The document declares its actions; a click inside it starts a new turn only for a declared action.',
});
