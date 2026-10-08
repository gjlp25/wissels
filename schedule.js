// Wisselschema-logica. Werkt in de browser (globals) en in Node (tests).
// KNVB-wedstrijdvormen seizoen 2026/'27. Een blok loopt tot de time-out of rust; de keeper wisselt alleen op een blokgrens.
const CATS = {
  JO7:  { field: 4, keeper: false, blocks: 6, block: 7.5,  label: 'JO7 – 4 tegen 4, 3 x 15 min, geen keeper' },
  JO8:  { field: 6, keeper: true,  blocks: 4, block: 10,   label: 'JO8 – 6 tegen 6, 2 x 20 min' },
  JO9:  { field: 6, keeper: true,  blocks: 4, block: 10,   label: 'JO9 – 6 tegen 6, 2 x 20 min' },
  JO10: { field: 6, keeper: true,  blocks: 4, block: 12.5, label: 'JO10 – 6 tegen 6, 2 x 25 min' },
  JO11: { field: 8, keeper: true,  blocks: 4, block: 15,   label: 'JO11 – 8 tegen 8, 2 x 30 min' },
  MO11: { field: 8, keeper: true,  blocks: 4, block: 15,   label: 'MO11 – 8 tegen 8, 2 x 30 min' },
  JO12: { field: 8, keeper: true,  blocks: 4, block: 15,   label: 'JO12 – 8 tegen 8, 2 x 30 min' },
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

// Vult m.slots en m.keeperBySlot. Eerlijk binnen de wedstrijd (minuten), en over wedstrijden (eerste wissel, tekort).
function generate(m, history) {
  const c = cat(m), s = stats(history), zero = { benchStarts: 0, diff: 0 }, st = id => s[id] || zero;
  const mins = {};
  m.present.forEach(id => mins[id] = 0);
  m.slots = [];
  m.keeperBySlot = [];
  for (let i = 0; i < c.blocks * c.block / m.interval; i++) {
    const kq = c.keeper ? m.keepers[Math.floor(i * m.interval / c.block)] : null;
    const k = m.present.includes(kq) ? kq : null;
    const prev = m.slots[i - 1] || [];
    const cands = shuffle(m.present.filter(id => id !== k)).sort((a, b) =>
      mins[a] - mins[b] ||
      (i === 0 ? st(b).benchStarts - st(a).benchStarts : 0) || // vaak eerste wissel geweest -> nu starten
      st(a).diff - st(b).diff ||                               // minutentekort uit vorige wedstrijden eerst
      prev.includes(b) - prev.includes(a));                    // zo min mogelijk wissels
    const on = (k ? [k] : []).concat(cands.slice(0, c.field - (k ? 1 : 0)));
    on.forEach(id => mins[id] += m.interval);
    m.slots.push(on);
    m.keeperBySlot.push(k);
  }
  return m;
}

if (typeof module !== 'undefined') module.exports = { CATS, cat, intervals, minutes, stats, generate };
