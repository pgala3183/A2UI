// OpenUI open-ended: one HtmlArtifact. Progress while the document line streams,
// Raw / Rendered tabs when it is complete, data pushed in from a statement.
import { startOpenUiApp } from '/shared/client.mjs';

await startOpenUiApp({
  mode: 'open-ended',
  title: 'HtmlArtifact(title, document, data)',
  prompts: ['Give me an interactive trip-cost calculator'],
  note: 'The document is one long statement. The page shows progress while it streams and mounts it in a sandbox once the server accepts the line. Bookings come back as a new "prices" statement.',
});
