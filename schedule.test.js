// Uitvoeren: node schedule.test.js
const assert = require('assert');
const { CATS, minutes, generate } = require('./schedule.js');
const FIELD = CATS.JO9.field;

const ids = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'];
const mk = (interval, keepers) => ({ present: ids, keepers, interval, slots: [], keeperBySlot: [] });
const A = ['a', 'a', 'a', 'a'];

// 5 min, 1 keeper: 8 veldspelers delen 5 plekken x 40 min -> iedereen precies 25 min
let m = generate(mk(5, A), []), min = minutes(m);
assert.strictEqual(min.a, 40);
ids.slice(1).forEach(id => assert.strictEqual(min[id], 25));
m.slots.forEach(on => assert.strictEqual(on.length, FIELD));

// 10 min: verschil binnen wedstrijd maximaal 10 min
m = generate(mk(10, A), []);
min = minutes(m);
const field = ids.slice(1).map(id => min[id]);
assert.ok(Math.max(...field) - Math.min(...field) <= 10);

// 5 min, keeper per kwart (kwart 3 geen keeper): keeper wisselt alleen op 10-minutengrens
m = generate(mk(5, ['a', 'b', null, 'c']), []);
assert.deepStrictEqual(m.keeperBySlot, ['a', 'a', 'b', 'b', null, null, 'c', 'c']);
m.slots.forEach(on => assert.strictEqual(on.length, FIELD));

// Afwezige keeper telt niet
m = generate({ ...mk(5, ['z', 'z', 'z', 'z']) }, []);
assert.deepStrictEqual(m.keeperBySlot, Array(8).fill(null));

// Eerste wissels rouleren: tweede wedstrijd niet dezelfde kinderen als eerste wissel
for (let run = 0; run < 50; run++) {
  const m1 = generate(mk(5, A), []), m2 = generate(mk(5, A), [m1]);
  const bench = x => ids.filter(id => !x.slots[0].includes(id));
  assert.deepStrictEqual(bench(m1).filter(id => bench(m2).includes(id)), []);
}

// Categorieën: aantal spelers en speeltijd volgens KNVB
const play = (c, keepers, interval) => {
  const m = generate({ cat: c, present: ids, keepers, interval, slots: [], keeperBySlot: [] }, []);
  return { m, total: m.slots.length * interval };
};
let r = play('JO10', A, 6.25);
assert.strictEqual(r.total, 50);
r.m.slots.forEach(on => assert.strictEqual(on.length, 6));
r = play('JO11', ['a', 'a', 'b', 'b'], 7.5);
assert.strictEqual(r.total, 60);
r.m.slots.forEach(on => assert.strictEqual(on.length, 8));
assert.deepStrictEqual(r.m.keeperBySlot, ['a', 'a', 'a', 'a', 'b', 'b', 'b', 'b']);
r = play('JO7', [], 7.5); // geen keeper, 4 spelers
assert.strictEqual(r.total, 45);
r.m.slots.forEach(on => assert.strictEqual(on.length, 4));
assert.deepStrictEqual(r.m.keeperBySlot, Array(6).fill(null));

console.log('ok');
