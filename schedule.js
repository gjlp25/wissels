// Wisselschema-logica. Werkt in de browser (globals) en in Node (tests).
const FIELD = 6, MATCH_MIN = 40, KEEPER_BLOCK = 10; // JO9: 6 tegen 6, 4x10 min, keeper minimaal per 10 min

// Wedstrijd: { present:[id], keepers:[id|null per kwart, 4x], interval:5|10, slots:[[ids op veld incl. keeper]], keeperBySlot:[id|null] }
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
  const s = stats(history), zero = { benchStarts: 0, diff: 0 }, st = id => s[id] || zero;
  const mins = {};
  m.present.forEach(id => mins[id] = 0);
  m.slots = [];
  m.keeperBySlot = [];
  for (let i = 0; i < MATCH_MIN / m.interval; i++) {
    const kq = m.keepers[Math.floor(i * m.interval / KEEPER_BLOCK)];
    const k = m.present.includes(kq) ? kq : null;
    const prev = m.slots[i - 1] || [];
    const cands = shuffle(m.present.filter(id => id !== k)).sort((a, b) =>
      mins[a] - mins[b] ||
      (i === 0 ? st(b).benchStarts - st(a).benchStarts : 0) || // vaak eerste wissel geweest -> nu starten
      st(a).diff - st(b).diff ||                               // minutentekort uit vorige wedstrijden eerst
      prev.includes(b) - prev.includes(a));                    // zo min mogelijk wissels
    const on = (k ? [k] : []).concat(cands.slice(0, FIELD - (k ? 1 : 0)));
    on.forEach(id => mins[id] += m.interval);
    m.slots.push(on);
    m.keeperBySlot.push(k);
  }
  return m;
}

if (typeof module !== 'undefined') module.exports = { FIELD, minutes, stats, generate };
