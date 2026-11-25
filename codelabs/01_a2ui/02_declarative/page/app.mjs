// A2UI declarative: same Basic Catalog renderer as the static step; the model
// now writes the components, so the page shows skeletons for ids that have
// not arrived yet and a correction note when validation fails.
import { startA2uiApp } from '/shared/client.mjs';

startA2uiApp({
  mode: 'declarative',
  title: 'The model writes the components',
  prompts: ['I found a broken bike, help me report it'],
  note: 'The reply streams one A2UI message per line. Attempt 1 uses a component the catalog does not have; the server returns the error and the model corrects itself.',
});
