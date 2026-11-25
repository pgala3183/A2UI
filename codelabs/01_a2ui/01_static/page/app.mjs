// A2UI static: the page knows the Basic Catalog; nothing else is custom.
import { startA2uiApp } from '/shared/client.mjs';

startA2uiApp({
  mode: 'static',
  title: 'Fixed templates, streaming data',
  prompts: ['How is Market St doing?', 'Show the network overview', 'How is the Ferry Building doing?'],
  note: 'The model only picks a hand-written template. Watch the wire: updateComponents arrives once, then only updateDataModel.',
});
