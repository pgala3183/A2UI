import test from 'node:test';
import assert from 'node:assert/strict';
import { Processor, messageKind } from '/shared/surface.mjs';

const v = 'v0.9';

test('components arrive in any order and are joined by id', () => {
  const p = new Processor();
  p.process({ version: v, createSurface: { surfaceId: 's', catalogId: 'basic' } });
  p.process({ version: v, updateComponents: { surfaceId: 's', components: [{ id: 'title', component: 'Text', text: 'Hi' }] } });
  const s = p.surfaces.get('s');
  assert.deepEqual(s.missing(), ['root']);
  p.process({ version: v, updateComponents: { surfaceId: 's', components: [{ id: 'root', component: 'Card', child: 'title' }] } });
  assert.deepEqual(s.missing(), []);
});

test('data model updates address a JSON Pointer and bindings resolve', () => {
  const p = new Processor();
  p.process({ version: v, createSurface: { surfaceId: 's', catalogId: 'basic' } });
  p.process({ version: v, updateDataModel: { surfaceId: 's', path: '/station', value: { bikes: 3 } } });
  p.process({ version: v, updateDataModel: { surfaceId: 's', path: '/station/bikes', value: 4 } });
  const s = p.surfaces.get('s');
  assert.equal(s.resolve({ path: '/station/bikes' }), 4);
  assert.equal(s.resolve('literal'), 'literal');
});

test('an action resolves its context from the data model at click time', () => {
  const p = new Processor();
  p.process({ version: v, createSurface: { surfaceId: 's', catalogId: 'basic' } });
  const s = p.surfaces.get('s');
  s.set('/report/bike', 'B-17');
  const envelope = s.action({ id: 'send', component: 'Button', action: { event: { name: 'report', context: { bike: { path: '/report/bike' }, kind: 'flat' } } } });
  assert.equal(envelope.action.name, 'report');
  assert.deepEqual(envelope.action.context, { bike: 'B-17', kind: 'flat' });
  assert.equal(envelope.action.sourceComponentId, 'send');
});

test('envelopes need exactly one kind; deleteSurface removes state', () => {
  assert.equal(messageKind({ version: v, createSurface: {}, deleteSurface: {} }), null);
  const p = new Processor();
  p.process({ version: v, createSurface: { surfaceId: 's', catalogId: 'basic' } });
  p.process({ version: v, deleteSurface: { surfaceId: 's' } });
  assert.equal(p.surfaces.size, 0);
  assert.throws(() => p.process({ version: v, updateDataModel: { surfaceId: 's', path: '/', value: {} } }));
});

test('pointer safety: prototype keys are refused', () => {
  const p = new Processor();
  p.process({ version: v, createSurface: { surfaceId: 's', catalogId: 'basic' } });
  assert.throws(() => p.process({ version: v, updateDataModel: { surfaceId: 's', path: '/__proto__/x', value: 1 } }));
});
