// json-render declarative: patches stream in; the page re-renders after each one.
import { startJsonRenderApp } from '/shared/client.mjs';

startJsonRenderApp({
  mode: 'declarative',
  title: 'Primitives, $state bindings, streamed patches',
  prompts: ['Build me a dashboard for the whole network'],
  note: 'Each wire entry is one JSON Patch operation. The card paints after the second one; numbers appear when /state arrives. Refresh sends back /state patches only.',
});
