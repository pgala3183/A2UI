// json-render open-ended: the registry's HtmlArtifact shows progress while
// chunks stream, then mounts the document in a sandbox and feeds it state.
import { startJsonRenderApp } from '/shared/client.mjs';

startJsonRenderApp({
  mode: 'open-ended',
  title: 'An HtmlArtifact streamed as patches',
  prompts: ['Give me an interactive trip-cost calculator'],
  note: 'The only catalog component is HtmlArtifact. Its HTML arrives as chunks appended with "-", and mounts only after the server lets the complete=true patch through.',
});
