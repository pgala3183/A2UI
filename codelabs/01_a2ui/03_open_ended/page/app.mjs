// A2UI open-ended: the renderer gains one custom component, HtmlFrame.
import { startA2uiApp } from '/shared/client.mjs';
import { custom } from '/shared/htmlframe.mjs';

startA2uiApp({
  mode: 'open-ended',
  title: 'A custom catalog with one HtmlFrame',
  prompts: ['Give me an interactive trip-cost calculator'],
  note: 'The model wrote the whole calculator as HTML. It runs in a sandboxed iframe, reads the A2UI data model, and its Book button becomes an A2UI action.',
  custom,
});
