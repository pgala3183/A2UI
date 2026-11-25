// Harness static: render tools draw pre-built components on the web surface.
import { startHarnessApp } from '/shared/client.mjs';

await startHarnessApp({
  mode: 'static',
  title: 'Render tools in the agent loop',
  prompts: ['Which stations need rebalancing?'],
  note: 'The agent reads data with a normal tool, then calls show_metric / show_chart / show_table. The same events are drawn here and in the server\'s terminal.',
});
