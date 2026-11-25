// Harness declarative: render_ui(spec) draws a validated element map.
import { startHarnessApp } from '/shared/client.mjs';

await startHarnessApp({
  mode: 'declarative',
  title: 'render_ui(spec): validation errors are tool results',
  prompts: ['Make me a rebalancing report'],
  note: 'The first render_ui call uses a type the catalog does not have. The tool returns the error as a result; the loop gives it to the model, which sends a fixed spec.',
});
