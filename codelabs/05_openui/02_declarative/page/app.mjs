// OpenUI declarative: forward references paint as skeletons until defined;
// a button's answer redefines a few statements and the page updates in place.
import { startOpenUiApp } from '/shared/client.mjs';

await startOpenUiApp({
  mode: 'declarative',
  title: 'Layouts with forward references',
  prompts: ['Build me a dashboard for the whole network'],
  note: 'root arrives first and names children that do not exist yet. Watch the skeletons fill in. The button\'s answer resends only 4 statements; each replaces the old one with the same id.',
});
