// json-render mixed: primitives + HtmlArtifact, setState in the browser,
// rebalance through the server. GET /text renders the same spec as text.
import { startJsonRenderApp } from '/shared/client.mjs';

startJsonRenderApp({
  mode: 'mixed',
  title: 'Primitives, one HtmlArtifact, two renderers',
  prompts: ['Build me a rebalancing desk'],
  note: 'The table toggle is the built-in setState (no request). The simulator\'s Apply sends rebalance to the server, which answers with /state patches. Open /text to see the same spec in a terminal renderer.',
});
