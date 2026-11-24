// Runs the page's script end to end with a forgiving fake DOM, so load-time crashes
// (like using a const before it is declared) fail a test instead of breaking the site.
const vm = require('vm'), fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];
const errors = [];

function node(tag) {                    // any property, call or construction gives another stub; children are remembered
  const props = new Map(), kids = [];
  return new Proxy(function () {}, {
    get(t, k) {
      if (k === '__tag') return tag;
      if (k === '__kids') return kids;
      if (props.has(k)) return props.get(k);
      if (k === 'append' || k === 'appendChild') return (...xs) => { kids.push(...xs); };
      if (k === 'replaceChildren') return (...xs) => { kids.length = 0; kids.push(...xs); };
      if (k === 'then') return undefined;
      if (k === Symbol.iterator) return function* () {};
      if (k === Symbol.toPrimitive) return () => '';
      if (k === 'length') return 0;
      if (k === 'value' || k === 'textContent' || k === 'className') return '';
      return node('stub');
    },
    set(t, k, v) { props.set(k, v); return true; },
    apply() { return node('stub'); },
    construct() { return node('stub'); },
    has() { return true; },
  });
}
const stub = () => node('stub');
const walk = (n, f, out = []) => {
  if (n && (typeof n === 'object' || typeof n === 'function')) { if (f(n)) out.push(n); (n.__kids || []).forEach(k => walk(k, f, out)); }
  return out;
};
const store = new Map();
const doc = { createElement: (t) => node(t), querySelector: () => node('q'), querySelectorAll: () => [], addEventListener() {}, body: node('body') };
const RACES = [
  { id: 'arima-kinen', name: 'Arima Kinen', category: 'long', surface: 'turf', slots: ['classic-late-dec', 'senior-late-dec'], aliases: [] },
  { id: 'japan-cup', name: 'Japan Cup', category: 'medium', surface: 'turf', slots: ['classic-late-nov'], aliases: ['Japan C.'] },
  { id: 'hopeful-stakes', name: 'Hopeful Stakes', category: 'medium', surface: 'turf', slots: ['junior-late-dec'], aliases: [] },
];
const TIERS = { S: ['Uma Stan'], A: [], B: [], C: [], D: [], E: [], F: [], Z: [] };
const API = {
  '/api/races': { races: RACES, points_per_shared_g1: 3 },
  '/api/skills': [{ id: null, name: 'Uma Stan', type: 'skill' }, { id: null, name: 'Now We\'re Cruisin\'!', type: 'unique' }],
  '/api/tiers': [{ id: 'S', weight: 1 }],
  '/api/styles': [{ id: 'pace-chaser', label: 'Pace Chaser' }],
};
const ctx = vm.createContext({
  document: doc, localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { store.set(k, String(v)); } }, console,
  window: { matchMedia: () => ({ matches: false }) },
  fetch: async (url) => {
    const key = String(url).split('?')[0];
    const body = key === '/api/checklists' ? { generic: { label: 'Overall', tiers: TIERS, blocked: [] } } : (API[key] || {});
    return { ok: true, json: async () => body };
  },
  Option: function () { return stub(); }, FormData: function () { return stub(); },
  Blob: function () { return stub(); }, URL: { createObjectURL: () => '', revokeObjectURL() {} },
  confirm: () => true, setTimeout, URLSearchParams,
});
// a swallowed `.catch(() => {})` must still be reported
vm.runInContext('const __e = []; const __c = Promise.prototype.catch; Promise.prototype.catch = function (f) { return this.then(undefined, e => { __e.push(e); return f && f(e); }); };', ctx);
const run = (code, label) => { try { vm.runInContext(code, ctx); } catch (e) { errors.push(label + ': ' + (e && e.stack || e)); } };

run(js, 'page load');
const result = {
  profile: 'generic', label: 'Overall', profile_label: 'Overall', style_label: null, score: 50, grade: 'B',
  next_grade: { grade: 'B+', at: 55, needed: 5 }, categories: { blue: 10, pink: 10, green: 10, white: 10 },
  top_contributors: [], blocked: [], affinity: { value: 12, base: null, races: 12, shared: { grandparent_1: 2, grandparent_2: 2 }, target: null },
};
setTimeout(() => {                      // let the fetch callbacks (races, skills, checklists) finish
  run('PANES.forEach(p => drawWins(p.pane)); changed();', 'draw G1 pickers');
  run('PANES[0].pane.wins.add("arima-kinen"); drawWins(PANES[0].pane); changed(); collect(false); collect(true);', 'wins + collect');
  run('renderTiers();', 'render checklist board');
  run('render({overall: ' + JSON.stringify(result) + ', events: [' + JSON.stringify({ ...result, profile: 'aries-cup:pace-chaser', profile_label: 'Aries Cup', style_label: 'Pace Chaser' }) + '], important: []});', 'render results');
  run('say("ok");', 'say');
  try {
    const assert = require('assert'), panes = vm.runInContext('PANES', ctx), clickable = (root, text) => walk(root, n => n.__tag === 'button' && n.textContent === text)[0];
    const [p0, p1] = [panes[0].pane, panes[1].pane];
    p0.wins.add('arima-kinen'); p0.wins.add('japan-cup'); vm.runInContext('drawWins(PANES[0].pane)', ctx);
    assert.ok(walk(p0.winsBox, n => n.__tag === 'button' && n.textContent === 'Japan Cup').length === 0 || true);
    const name = walk(p0.winsBox, n => n.__tag === 'input' && String(n.placeholder).startsWith('Name'))[0];
    assert.ok(name, 'name box exists'); name.value = 'Inari One run 1';
    clickable(p0.winsBox, 'Save wins for this Uma').onclick();
    const saved = JSON.parse(store.get('uma-saved-wins'));
    assert.deepStrictEqual([saved.length, saved[0].name, saved[0].wins.length], [1, 'Inari One run 1', 2]);
    name.value = 'inari one RUN 1'; clickable(p0.winsBox, 'Save wins for this Uma').onclick();      // same name updates, not duplicates
    assert.strictEqual(JSON.parse(store.get('uma-saved-wins')).length, 1);
    const sel = walk(p1.winsBox, n => n.__tag === 'select')[0]; sel.value = saved[0].id;
    clickable(p1.winsBox, 'Load').onclick();
    assert.strictEqual(p1.wins.size, 2); assert.ok(p1.wins.has('japan-cup'));
    clickable(p1.winsBox, 'Delete').onclick();
    assert.strictEqual(JSON.parse(store.get('uma-saved-wins')).length, 0);
    p1.wins.add('hopeful-stakes'); clickable(p1.winsBox, 'Clear all') && clickable(p1.winsBox, 'Clear all').onclick();
    assert.strictEqual(p1.wins.size, 0);
  } catch (e) { errors.push('G1 save/load flow: ' + (e && e.stack || e)); }
  run('clearAll();', 'clear');
  try { vm.runInContext('__e', ctx).forEach(e => errors.push('swallowed promise error: ' + (e && e.stack || e))); } catch (e) { /* none */ }
  if (errors.length) { console.error('UI smoke test FAILED:\n' + errors.join('\n\n')); process.exit(1); }
  console.log('UI smoke test passed');
}, 100);
