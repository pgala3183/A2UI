// Harness mixed: alert (static), spec (declarative), embedded simulator
// (open-ended), and a permission gate on the one tool with side effects.
import { startHarnessApp } from '/shared/client.mjs';

await startHarnessApp({
  mode: 'mixed',
  title: 'Every kind of generative UI in one agent loop',
  prompts: ['Build me a rebalancing desk'],
  note: 'Rendering is allowed: it is sandboxed and validated. Moving bikes is not, until you approve. Both the spec button and the simulator send actions the views declared.',
});
