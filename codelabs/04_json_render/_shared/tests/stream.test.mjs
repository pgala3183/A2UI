import test from 'node:test';
import assert from 'node:assert/strict';
import { createSpecStreamCompiler } from '/shared/stream.mjs';
import { resolve } from '/shared/spec.mjs';

test('lines become patches only when complete', () => {
  const c = createSpecStreamCompiler();
  let out = c.push('{"op":"add","path":"/root","value":"da');
  assert.equal(out.patches.length, 0);
  out = c.push('sh"}\n{"op":"add","path":"/elements/dash","value":{"type":"Card","props":{}}}\n');
  assert.equal(out.patches.length, 2);
  assert.equal(out.spec.root, 'dash');
  assert.equal(out.spec.elements.dash.type, 'Card');
});

test('appending to an array with "-" streams a document in chunks', () => {
  const c = createSpecStreamCompiler();
  c.push('{"op":"add","path":"/elements/a","value":{"type":"HtmlArtifact","props":{"chunks":[]}}}\n');
  c.push('{"op":"add","path":"/elements/a/props/chunks/-","value":"<p>"}\n{"op":"add","path":"/elements/a/props/chunks/-","value":"hi</p>"}\n');
  assert.equal(c.spec.elements.a.props.chunks.join(''), '<p>hi</p>');
});

test('$state bindings and $not resolve against state', () => {
  const state = { summary: { bikes: 49 }, ui: { open: false } };
  assert.deepEqual(resolve({ label: 'Bikes', value: { $state: '/summary/bikes' } }, state), { label: 'Bikes', value: 49 });
  assert.equal(resolve({ $not: { $state: '/ui/open' } }, state), true);
});
