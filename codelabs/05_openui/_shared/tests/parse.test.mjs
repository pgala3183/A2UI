import test from 'node:test';
import assert from 'node:assert/strict';
import { Program, parseStatement, resolve, tokenize } from '/shared/openui-parse.mjs';

const library = { Card: { params: [{ name: 'title' }, { name: 'children' }] }, Text: { params: [{ name: 'text' }, { name: 'variant' }] } };

test('a statement is id = expression', () => {
  assert.deepEqual(parseStatement('t = Text("Hi", "h2")'), ['t', ['call', 'Text', [['lit', 'Hi'], ['lit', 'h2']]]]);
  assert.deepEqual(parseStatement('xs = [1, "a", true, null, {"k": 2}]')[1][0], 'list');
});

test('strings keep JSON escapes, including quotes and newlines', () => {
  const [, node] = parseStatement('doc = "<p class=\\"x\\">a\\nb</p>"');
  assert.equal(node[1], '<p class="x">a\nb</p>');
});

test('streaming: only complete lines are returned; the rest waits', () => {
  const p = new Program();
  assert.deepEqual(p.feed('root = Card("A", [t])\nt = Te'), ['root = Card("A", [t])']);
  assert.deepEqual(p.pending(), { id: 't', component: 'Te', chars: 6 });
  assert.deepEqual(p.feed('xt("hello")\n'), ['t = Text("hello")']);
});

test('forward references, overrides and cycles', () => {
  const p = new Program();
  p.add('root = Card("A", [t, u])');
  p.add('t = Text("one")');
  let tree = resolve(p, library);
  assert.equal(tree.props.children[0].props.text, 'one');
  assert.equal(tree.props.children[1].type, '__missing');
  p.add('t = Text("two")');
  tree = resolve(p, library);
  assert.equal(tree.props.children[0].props.text, 'two');
  p.add('u = Card("loop", [root])');
  assert.equal(resolve(p, library).props.children[1].props.children[0].type, '__cycle');
});

test('bad input fails loudly', () => {
  assert.throws(() => parseStatement('Root = Text("x")'));
  assert.throws(() => parseStatement('a = Text("x"'));
  assert.throws(() => tokenize('a = @'));
});
