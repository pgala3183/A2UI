// A2UI mixed: Basic Catalog renderer + the HtmlFrame extension, one surface.
import { startA2uiApp } from '/shared/client.mjs';
import { custom } from '/shared/htmlframe.mjs';

startA2uiApp({
  mode: 'mixed',
  title: 'Catalog components plus one HtmlFrame',
  prompts: ['Build me a rebalancing desk for the network'],
  note: 'Numbers, text and the button are catalog components. Only the simulator is model-written HTML. One updateDataModel refreshes both, and the iframe keeps its state.',
  custom,
});
