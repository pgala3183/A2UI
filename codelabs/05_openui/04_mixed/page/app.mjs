// OpenUI mixed: library components + one HtmlArtifact; updates are statements.
import { startOpenUiApp } from '/shared/client.mjs';

await startOpenUiApp({
  mode: 'mixed',
  title: 'Library components plus one HtmlArtifact',
  prompts: ['Build me a rebalancing desk'],
  note: 'Everything but the simulator is library components. Actions come back as a handful of statements that replace old ones by id; the simulator\'s document is unchanged, so its iframe keeps running.',
});
