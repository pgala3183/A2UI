import test from 'node:test';
import assert from 'node:assert/strict';
import { applyPatch, getPointer, setPointer } from '/common/jsonpatch.mjs';
import { parsePartial } from '/common/partial-json.mjs';
import { parseFrame, splitFrames } from '/common/sse.mjs';
import { prepare, cleanPayload } from '/common/sandbox.mjs';

test('json patch twin: add, replace, remove, append', () => {
  const doc = applyPatch({ a: { b: [1] } }, [
    { op: 'add', path: '/a/b/-', value: 2 }, { op: 'replace', path: '/a/b/0', value: 0 },
    { op: 'add', path: '/c', value: { d: 1 } }, { op: 'remove', path: '/c/d' }]);
  assert.deepEqual(doc, { a: { b: [0, 2] }, c: {} });
  assert.throws(() => setPointer({}, '/__proto__/x', 1));
  assert.equal(getPointer({ a: [5] }, '/a/0'), 5);
});

test('partial JSON: usable values before the JSON is complete', () => {
  assert.deepEqual(parsePartial('{"name": "Mar'), { name: 'Mar' });
  assert.deepEqual(parsePartial('{"a": 1, "b'), { a: 1 });
  assert.deepEqual(parsePartial('{"a": [1, 2'), { a: [1, 2] });
  assert.deepEqual(parsePartial('{"a": {"b": "x'), { a: { b: 'x' } });
  assert.equal(parsePartial(''), undefined);
});

test('SSE frames split and parse', () => {
  const [frames, rest] = splitFrames('data: {"a":1}\n\nevent: note\ndata: {"b":2}\n\ndata: {"c"');
  assert.equal(frames.length, 2);
  assert.equal(rest, 'data: {"c"');
  assert.deepEqual(parseFrame(frames[1]), { event: 'note', data: { b: 2 } });
});

test('sandbox: CSP and bridge go first in <head>; payloads are cleaned', () => {
  const html = prepare('<html><head><title>x</title></head><body></body></html>');
  assert.ok(html.indexOf('Content-Security-Policy') < html.indexOf('<title>'));
  assert.ok(html.includes('window.genui'));
  assert.deepEqual(cleanPayload({ a: 1 }), { a: 1 });
  assert.deepEqual(cleanPayload({ big: 'x'.repeat(20000) }), { error: 'payload too large' });
});
