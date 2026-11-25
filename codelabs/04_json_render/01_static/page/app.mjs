// json-render static: the registry has whole widgets; the spec has one element.
import { startJsonRenderApp } from '/shared/client.mjs';

startJsonRenderApp({
  mode: 'static',
  title: 'A catalog of whole widgets',
  prompts: ['How is Market St doing?', 'How is the Ferry Building doing?', 'How much is a 30 minute ride?'],
  note: 'The catalog is the prompt, the validator and the registry. Attempt 1 puts a string where the catalog wants an integer; the validator says so and the model fixes it.',
});
