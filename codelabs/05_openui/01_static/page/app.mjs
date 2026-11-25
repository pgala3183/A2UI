// OpenUI static: the library has whole widgets; the program is one statement.
import { startOpenUiApp } from '/shared/client.mjs';

await startOpenUiApp({
  mode: 'static',
  title: 'One statement picks a widget',
  prompts: ['How is Market St doing?', 'How is the Ferry Building doing?', 'How much is a 30 minute ride?'],
  note: 'The model answers with a single line: root = StationCard("...", 3, 22, ...). Arguments are positional; the library knows their names.',
});
