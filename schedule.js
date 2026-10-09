// Wisselschema-logica. Werkt in de browser (globals) en in Node (tests).
// KNVB-wedstrijdvormen seizoen 2026/'27. Een blok loopt tot de time-out of rust; de keeper wisselt alleen op een blokgrens.
const CATS = {
  JO7:  { field: 4, keeper: false, blocks: 6, block: 7.5,  label: 'JO7: 4 tegen 4, 3 x 15 min, geen keeper' },
  JO8:  { field: 6, keeper: true,  blocks: 4, block: 10,   label: 'JO8: 6 tegen 6, 2 x 20 min' },
  JO9:  { field: 6, keeper: true,  blocks: 4, block: 10,   label: 'JO9: 6 tegen 6, 2 x 20 min' },
  JO10: { field: 6, keeper: true,  blocks: 4, block: 12.5, label: 'JO10: 6 tegen 6, 2 x 25 min' },
  JO11: { field: 8, keeper: true,  blocks: 4, block: 15,   label: 'JO11: 8 tegen 8, 2 x 30 min' },
  MO11: { field: 8, keeper: true,  blocks: 4, block: 15,   label: 'MO11: 8 tegen 8, 2 x 30 min' },
  JO12: { field: 8, keeper: true,  blocks: 4, block: 15,   label: 'JO12: 8 tegen 8, 2 x 30 min' },
};
const cat = m => CATS[m.cat] || CATS.JO9;
const intervals = c => [c.block / 2, c.block]; // wisselen per half blok of per blok

// Wedstrijd: { cat, present:[id], keepers:[id|null per blok], interval, slots:[[ids op veld incl. keeper]], keeperBySlot:[id|null] }
function minutes(m) {
  const r = {};
  m.present.forEach(id => r[id] = 0);
  m.slots.forEach(on => on.forEach(id => { if (id in r) r[id] += m.interval; }));
  return r;
}

// Totalen over eerdere wedstrijden. diff = minuten t.o.v. wedstrijdgemiddelde (negatief = tekort).
function stats(history) {
  const s = {};
  const get = id => s[id] ??= { matches: 0, minutes: 0, benchStarts: 0, keeper: 0, diff: 0 };
  history.filter(m => m.slots.length).forEach(m => {
    const min = minutes(m), avg = m.present.reduce((t, id) => t + min[id], 0) / m.present.length;
    m.present.forEach(id => {
      const p = get(id);
      p.matches++;
      p.minutes += min[id];
      p.diff += min[id] - avg;
      if (!m.slots[0].includes(id)) p.benchStarts++;
    });
    m.keeperBySlot.forEach(k => { if (k) get(k).keeper += m.interval; });
  });
  return s;
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

// Minimize consecutive bench occurrences across the whole schedule first.
// Only selected keepers need distinct lookahead states (at most four in CATS).
// Other players are interchangeable for feasibility; choose their identities fairly.
function generate(m, history) {
  const c = cat(m), s = stats(history), zero = { benchStarts: 0, diff: 0 }, st = id => s[id] || zero;
  const size = Math.min(c.field, m.present.length), mins = Object.fromEntries(m.present.map(id => [id, 0]));
  const keepers = Array.from({ length: c.blocks * c.block / m.interval }, (_, i) => {
    const k = c.keeper ? m.keepers[Math.floor(i * m.interval / c.block)] : null;
    return m.present.includes(k) ? k : null;
  });
  const special = [...new Set(keepers.filter(k => k !== null))];
  const ordinary = m.present.filter(id => !special.includes(id));
  const ordinaryIds = new Set(ordinary);
  const states = [];
  for (let mask = 0; mask < 2 ** special.length; mask++) {
    const on = special.filter((_, j) => mask & (2 ** j)), count = size - on.length;
    if (count >= 0 && count <= ordinary.length) states.push({ on, count });
  }
  const allowed = keepers.map(k => states.filter(x => k === null || x.on.includes(k)));
  // Minimum overlap of the two ordinary bench sets, plus actual keeper bench overlap.
  const cost = (a, b) => Math.max(0, ordinary.length - a.count - b.count) +
    special.filter(id => !a.on.includes(id) && !b.on.includes(id)).length;
  const future = allowed.map(() => new Map());
  for (let i = allowed.length - 1; i >= 0; i--) {
    for (const a of allowed[i]) future[i].set(a, i === allowed.length - 1 ? 0 :
      Math.min(...allowed[i + 1].map(b => cost(a, b) + future[i + 1].get(b))));
  }
  m.slots = [];
  m.keeperBySlot = keepers;
  let previous;
  for (let i = 0; i < keepers.length; i++) {
    const prev = m.slots[i - 1] || [];
    const ranked = shuffle(m.present.slice()).sort((a, b) =>
      mins[a] - mins[b] ||
      (i === 0 ? st(b).benchStarts - st(a).benchStarts : 0) ||
      st(a).diff - st(b).diff || prev.includes(b) - prev.includes(a));
    const rankedOrdinary = ranked.filter(id => ordinaryIds.has(id));
    // Bringing ordinary bench players on first realizes the transition's minimum.
    if (i) rankedOrdinary.sort((a, b) => prev.includes(a) - prev.includes(b));
    const minimum = Math.min(...allowed[i].map(a => (previous ? cost(previous, a) : 0) + future[i].get(a)));
    const choices = allowed[i].filter(a => (previous ? cost(previous, a) : 0) + future[i].get(a) === minimum)
      .map(a => ({ state: a, on: a.on.concat(rankedOrdinary.slice(0, a.count)) }));
    // Lexicographic priority: minutes, bench starts, historical deficit, then switches.
    choices.sort((a, b) => {
      for (const id of ranked) {
        const diff = Number(b.on.includes(id)) - Number(a.on.includes(id));
        if (diff) return diff;
      }
      return 0;
    });
    const { state, on } = choices[0];
    previous = state;
    on.forEach(id => mins[id] += m.interval);
    m.slots.push(on);
  }
  return m;
}

if (typeof module !== 'undefined') module.exports = { CATS, cat, intervals, minutes, stats, generate };
