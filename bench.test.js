const { test } = require('node:test');
const assert = require('node:assert/strict');
const { CATS, generate } = require('./schedule');
const ids = n => Array.from({ length: n }, (_, i) => `p${i}`);
const match = (n, cat = 'JO9', half = false, keepers = []) => ({ status: 'played', cat, present: ids(n), interval: CATS[cat].block / (half ? 2 : 1), keepers, slots: [], keeperBySlot: [] });
const repeats = m => m.slots.slice(1).reduce((sum, on, i) => sum + m.present.filter(id => !on.includes(id) && !m.slots[i].includes(id)).length, 0);
function valid(m) {
  for (const [i, on] of m.slots.entries()) {
    assert.equal(on.length, Math.min(m.present.length, CATS[m.cat].field));
    assert.equal(new Set(on).size, on.length);
    assert.ok(on.every(id => m.present.includes(id)));
    assert.ok(!m.keeperBySlot[i] || on.includes(m.keeperBySlot[i]));
  }
}
// Independent exhaustive oracle enumerates complete field subsets, not keeper groups.
function oracle(m) {
  const c = CATS[m.cat], size = Math.min(m.present.length, c.field), sets = [];
  function combinations(start, on) {
    if (on.length === size) { sets.push(on); return; }
    for (let i = start; i < m.present.length; i++) combinations(i + 1, [...on, m.present[i]]);
  }
  combinations(0, []);
  let costs = new Map();
  for (let i = 0; i < c.blocks * c.block / m.interval; i++) {
    const k = c.keeper ? m.keepers[Math.floor(i * m.interval / c.block)] : null;
    const next = new Map();
    for (const on of sets.filter(on => !m.present.includes(k) || on.includes(k))) {
      let cost = i ? Infinity : 0;
      for (const [prev, prior] of costs) cost = Math.min(cost, prior + m.present.filter(id => !on.includes(id) && !prev.includes(id)).length);
      next.set(on, cost);
    }
    costs = next;
  }
  return Math.min(...costs.values());
}
function seeded(seed, fn) {
  const original = Math.random;
  Math.random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32);
  try { return fn(); } finally { Math.random = original; }
}
test('brings every previously benched player back despite keeper minute imbalance', () => {
  for (let seed = 1; seed <= 40; seed++) seeded(seed, () => {
    const m = generate(match(9, 'JO9', true, ['p0', 'p1', 'p2', 'p3']), []);
    valid(m); assert.equal(repeats(m), 0);
  });
});
test('looks ahead to keepers at full capacity instead of creating avoidable bench runs', () => {
  for (let seed = 1; seed <= 40; seed++) seeded(seed, () => {
    const m = generate(match(12, 'JO9', false, ['p0', 'p1', 'p0', 'p1']), []);
    valid(m); assert.equal(repeats(m), 0);
  });
});
test('minimizes unavoidable repeats with a fixed keeper and oversized squad', () => {
  for (const n of [12, 13, 20, 65]) {
    const m = generate(match(n, 'JO9', true, Array(4).fill('p0')), []);
    valid(m); assert.equal(repeats(m), (n - 11) * 7);
  }
});
test('matches exhaustive minimum for small squads and all keeper choices', () => {
  for (const n of [0, 3, 6, 7]) for (const half of [false, true]) {
    for (let code = 0; code < 81; code++) {
      let x = code; const keepers = Array.from({ length: 4 }, () => { const k = [null, 'p0', 'p1'][x % 3]; x = Math.floor(x / 3); return k; });
      const m = match(n, 'JO9', half, keepers), want = oracle(m);
      seeded(code + 1, () => generate(m, [])); valid(m); assert.equal(repeats(m), want, JSON.stringify({ n, half, keepers }));
    }
  }
});
test('exhaustive oracle checks tight capacity, infeasible squads and keeper parity conflicts', () => {
  const patterns = [[], ['p0','p1','p0','p1'], ['p0','p1','p2','p3'], ['p0','p1','p1','p0'], ['p0','p0','p0','p0'], ['p0',null,'p1',null]];
  for (const [cat, n] of [['JO7',8], ['JO7',9], ['JO9',10], ['JO9',12]]) for (const keepers of patterns) {
    const m = match(n, cat, false, keepers), want = oracle(m);
    seeded(n + keepers.length, () => generate(m, [])); valid(m); assert.equal(repeats(m), want, JSON.stringify({cat,n,keepers}));
  }
});
test('four, six and eight field boundaries include fixed, absent and rotating keepers', () => {
  for (const cat of ['JO7','JO9','JO11']) for (const half of [false,true]) {
    const c = CATS[cat], slots = c.blocks * (half ? 2 : 1);
    for (const [n, keepers, want] of [
      [2*c.field, Array(c.blocks).fill(null), 0],
      [2*c.field, Array(c.blocks).fill('absent'), 0],
      [2*c.field+3, Array(c.blocks).fill(null), 3*(slots-1)],
      [2*c.field, Array(c.blocks).fill('p0'), c.keeper ? slots-1 : 0],
    ]) {
      const m = generate(match(n,cat,half,keepers), []); valid(m); assert.equal(repeats(m),want);
    }
    if (c.keeper && !half) {
      const m = generate(match(2*c.field,cat,false,Array.from({length:c.blocks},(_,i)=>`p${i%2}`)), []);
      valid(m); assert.equal(repeats(m),0);
    }
  }
});
test('categories, intervals, absent keepers and randomized history preserve rotation', () => {
  for (const cat of Object.keys(CATS)) for (const half of [false, true]) for (let seed = 1; seed <= 20; seed++) seeded(seed, () => {
    const c = CATS[cat], n = c.field + seed % c.field;
    const keepers = Array.from({ length: c.blocks }, (_, i) => [null, 'absent', `p${i % n}`][(seed + i) % 3]);
    const old = generate(match(n, cat, half, keepers), []);
    const m = generate(match(n, cat, half, keepers), [old]); valid(m); assert.equal(repeats(m), 0);
  });
});
