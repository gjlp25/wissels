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
  const r = Object.create(null);
  m.present.forEach(id => r[id] = 0);
  m.slots.forEach(on => on.forEach(id => { if (id in r) r[id] += m.interval; }));
  return r;
}

// Totalen over eerdere wedstrijden. diff = minuten t.o.v. wedstrijdgemiddelde (negatief = tekort).
function stats(history) {
  const s = Object.create(null);
  const get = id => s[id] ??= { matches: 0, minutes: 0, benchStarts: 0, keeper: 0, diff: 0 };
  history.filter(m => matchStatus(m).value === 'played' && m.slots.length).forEach(m => {
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

// Legacy dates are evidence of preparation, not proof of play. Never write inferred status.
const localDay = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
function matchStatus(m, today = localDay()) {
  return m.status ? { value: m.status, inferred: false }
    : { value: m.date && m.date < today ? 'played' : 'ready', inferred: true };
}

// Preserve pre-team player/match IDs and saved schedules during the existing migration.
function upgradeLegacy(input) {
  if (!input || input.teams !== undefined || !Array.isArray(input.players) || !Array.isArray(input.matches)) return input;
  const t = { id: 'legacy-team', name: 'Mijn team', players: input.players };
  const result = { ...input, teams: [t], team: t.id, matches: input.matches.map(m => ({ ...m, teamId: t.id,
    keepers: Array.from({ length: 4 }, (_, q) => m.keepers?.[q % m.keepers.length] ?? null) })) };
  delete result.players;
  return result;
}
// Validate before replacing any browser state. Historical deleted-player references are allowed.
function validateBackup(input) {
  const fail = () => { throw new Error('Dit is geen geldig back-upbestand: controleer teams, spelers, wedstrijden en schema’s.'); };
  const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
  const id = x => typeof x === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(x) && !['constructor', 'prototype', '__proto__'].includes(x);
  // Check the original legacy list before cycling/truncating it to four blocks.
  if (input?.teams === undefined && Array.isArray(input?.players)) {
    if (!Array.isArray(input.matches) || !input.matches.every(m => object(m) && Array.isArray(m.present) && Array.isArray(m.keepers) &&
      m.keepers.every(k => k === null || (id(k) && m.present.includes(k))))) fail();
  }
  input = upgradeLegacy(input);
  const ids = x => Array.isArray(x) && x.every(id) && new Set(x).size === x.length;
  const text = x => typeof x === 'string';
  if (!object(input) || !Array.isArray(input.teams) || !Array.isArray(input.matches)) fail();
  if (input.version !== undefined && input.version !== 1) fail();
  if (!ids(input.teams.map(t => t?.id)) || !ids(input.matches.map(m => m?.id))) fail();
  for (const t of input.teams) {
    if (!object(t) || !text(t.name) || !Array.isArray(t.players) || (t.cat !== undefined && (!text(t.cat) || !Object.hasOwn(CATS, t.cat)))) fail();
    if (!ids(t.players.map(p => p?.id))) fail();
    for (const p of t.players) { if (!object(p) || !id(p.id) || !text(p.name)) fail(); }
  }
  if (input.team !== undefined && !input.teams.some(t => t.id === input.team)) fail();
  const validSchedule = m => {
    if (!object(m) || (m.cat !== undefined && (!text(m.cat) || !Object.hasOwn(CATS, m.cat))) || !intervals(cat(m)).includes(m.interval) || !ids(m.present)) fail();
    if (!Array.isArray(m.keepers) || m.keepers.length > cat(m).blocks || !m.keepers.every(k => k === null || (id(k) && m.present.includes(k)))) fail();
    if (!Array.isArray(m.slots) || m.slots.length > cat(m).blocks * cat(m).block / m.interval || !m.slots.every(on => ids(on) && on.every(p => m.present.includes(p)))) fail();
    if (!Array.isArray(m.keeperBySlot) || m.keeperBySlot.length !== m.slots.length || !m.keeperBySlot.every((k, i) => k === null || (id(k) && m.slots[i].includes(k)))) fail();
    if (!object(m.pos) || !Object.entries(m.pos).every(([k, p]) => (k === 'K' || id(k)) && Array.isArray(p) && p.length === 2 && p.every(n => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 100))) fail();
    if (m.manual !== undefined && typeof m.manual !== 'boolean') fail();
  };
  for (const m of input.matches) {
    if (!object(m) || !input.teams.some(t => t.id === m.teamId) || !text(m.opponent) || !text(m.date)) fail();
    if (m.date && (!/^\d{4}-\d{2}-\d{2}$/.test(m.date) || !Number.isFinite(Date.parse(m.date)) || new Date(m.date).toISOString().slice(0, 10) !== m.date)) fail();
    if (m.status !== undefined && !['draft', 'ready', 'played'].includes(m.status)) fail();
    validSchedule(m);
    if (m.undo !== undefined) {
      if (!object(m.undo) || Object.keys(m.undo).some(k => !['cat', 'interval', 'present', 'keepers', 'slots', 'keeperBySlot', 'pos', 'manual'].includes(k))) fail();
      validSchedule(m.undo);
    }
  }
  if (input.backup !== undefined && (!object(input.backup) || !text(input.backup.lastExportAt) || !Number.isFinite(Date.parse(input.backup.lastExportAt)) || !Number.isInteger(input.backup.playedAtExport) || input.backup.playedAtExport < 0)) fail();
  return JSON.parse(JSON.stringify(input));
}

if (typeof module !== 'undefined') module.exports = { CATS, cat, intervals, minutes, stats, generate, localDay, matchStatus, validateBackup, upgradeLegacy };
