import { createStore, initialState, writeHash, applyFilters, VANCOUVER } from './state.js';
import { buildLayers } from './layers/index.js';
import { buildEffects } from './effects/index.js';
import { loadBuildings, bboxAround, loadIndex } from './layers/existing.js';
import { toRenderItems } from './layers/developments.js';
import { geocode } from './geocode.js';
import { mountFilters, renderNearby, distM } from './ui/filters.js';
import { developmentHtml, tooltip } from './ui/details.js';

const BASEMAP = 'https://tiles.openfreemap.org/styles/positron';
const FALLBACK_STYLE = {
  version: 8, sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#e9ecf0' } }],
};

const store = createStore(initialState());
const $ = (s) => document.querySelector(s);

// ---------- map ----------
async function pickStyle() {
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 6000);
    const r = await fetch(BASEMAP, { signal: ctl.signal });
    clearTimeout(t);
    if (r.ok) return await r.json();
  } catch { /* fall through */ }
  $('#basemap-note').hidden = false;
  return FALLBACK_STYLE;
}

const start = store.get().address ?? VANCOUVER;
const map = new maplibregl.Map({
  container: 'map',
  style: await pickStyle(),
  center: [start.lon, start.lat],
  zoom: store.get().address ? 16.3 : 12.5,
  pitch: 55,
  bearing: -25,
  maxPitch: 85,
  canvasContextAttributes: { antialias: true },
  attributionControl: { compact: true },
});
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');

const popup = new maplibregl.Popup({ closeButton: true, maxWidth: '320px' });
const overlay = new deck.MapboxOverlay({
  interleaved: true,
  layers: [],
  getTooltip: tooltip,
  onClick: ({ object, layer, coordinate }) => {
    if (!object || layer?.id !== 'developments') return;
    popup.setLngLat(coordinate).setHTML(developmentHtml(object.p)).addTo(map);
  },
});
map.addControl(overlay);

// ---------- render pipeline ----------
let runtime = { buildings: [], filtered: [], developmentItems: [], version: 0 };
let lastKey = null;

function render(state) {
  const key = JSON.stringify(state.filters) + '|' + state.developments.length;
  if (key !== lastKey) {
    lastKey = key;
    runtime.filtered = applyFilters(state.developments, state.filters);
    runtime.developmentItems = runtime.filtered.flatMap(toRenderItems);
    runtime.version++;
  }
  overlay.setProps({ layers: buildLayers(state, runtime), effects: buildEffects(state) });
  $('#match-count').textContent = `${runtime.filtered.length} matching development${runtime.filtered.length === 1 ? '' : 's'}`;
  renderNearby($('#nearby'), state.address, runtime.filtered, flyToFeature);
  writeHash(state);
}
store.subscribe(render);

// ---------- existing buildings (chunked, follows the camera) ----------
let loadSeq = 0;
async function refreshBuildings() {
  if (map.getZoom() < 14) return;
  const b = map.getBounds();
  const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
  const addr = store.get().address;
  const seq = ++loadSeq;
  const [view, near] = await Promise.all([
    loadBuildings(bbox),
    addr ? loadBuildings(bboxAround(addr.lon, addr.lat, 1500)) : [],
  ]);
  if (seq !== loadSeq || view == null) return;
  const set = new Set(view);
  for (const x of near ?? []) set.add(x);
  runtime.buildings = [...set];
  render(store.get());
}
map.on('moveend', refreshBuildings);

// ---------- camera ----------
function flyTo(lon, lat, opts = {}) {
  map.flyTo({ center: [lon, lat], zoom: 16.4, pitch: 60, bearing: map.getBearing() || -25, duration: 2200, essential: true, ...opts });
}
function flyToFeature(ft) {
  const p = ft.properties;
  flyTo(p.lon, p.lat, { zoom: 17 });
  popup.setLngLat([p.lon, p.lat]).setHTML(developmentHtml(p)).addTo(map);
}
const cam = {
  top: () => map.easeTo({ pitch: 0, duration: 800 }),
  oblique: () => map.easeTo({ pitch: 60, duration: 800 }),
  street: () => map.easeTo({ pitch: 82, zoom: Math.max(map.getZoom(), 17), duration: 1000 }),
  left: () => map.easeTo({ bearing: map.getBearing() - 45, duration: 600 }),
  right: () => map.easeTo({ bearing: map.getBearing() + 45, duration: 600 }),
  north: () => map.easeTo({ bearing: 0, duration: 600 }),
  home: () => { const a = store.get().address; if (a) flyTo(a.lon, a.lat); },
};
document.querySelectorAll('[data-cam]').forEach((b) => b.addEventListener('click', () => cam[b.dataset.cam]()));

// ---------- address search ----------
const form = $('#search'), results = $('#results'), status = $('#search-status');
const pin = new maplibregl.Marker({ color: '#1a6dff' });
function choose(r, alternatives = []) {
  results.innerHTML = '';
  pin.setLngLat([r.lon, r.lat]).addTo(map);
  $('#q').value = r.label;
  store.set({ address: r });
  flyTo(r.lon, r.lat);
  if (alternatives.length) {
    const head = document.createElement('li');
    head.className = 'muted alt-head';
    head.textContent = 'Not it? Other matches:';
    results.appendChild(head);
    alternatives.forEach((a) => {
      const li = document.createElement('li');
      li.textContent = a.label;
      li.addEventListener('click', () => choose(a));
      results.appendChild(li);
    });
  }
}
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  status.textContent = 'Searching…';
  results.innerHTML = '';
  try {
    const res = await geocode($('#q').value);
    status.textContent = res.length ? '' : 'No match in Vancouver. Try adding the street type (St, Ave).';
    if (res.length) {
      // Nominatim often returns several businesses inside the same building; keep distinct places only.
      const alts = [];
      for (const r of res.slice(1)) {
        if ([res[0], ...alts].every((x) => x.label !== r.label && distM(x, r) > 40)) alts.push(r);
      }
      choose(res[0], alts);
    }
  } catch (err) {
    status.textContent = `Search failed: ${err.message}`;
  }
});

// ---------- data ----------
async function loadData() {
  try {
    const [g, meta, cones] = await Promise.all([
      fetch('data/developments.geojson').then((r) => (r.ok ? r.json() : null)),
      fetch('data/meta.json').then((r) => (r.ok ? r.json() : null)),
      fetch('data/view_cones.geojson').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]);
    runtime.viewCones = cones;
    if (!g) throw new Error('missing');
    store.set({ developments: g.features, meta });
    if (meta?.generated_at) $('#data-date').textContent = `Data updated ${meta.generated_at.slice(0, 10)}`;
  } catch {
    $('#data-note').hidden = false;
  }
}

mountFilters($('#filters'), store);
if (store.get().address) {
  pin.setLngLat([store.get().address.lon, store.get().address.lat]).addTo(map);
  $('#q').value = store.get().address.label;
}
$('#panel-toggle').addEventListener('click', () => document.body.classList.toggle('panel-collapsed'));
map.once('load', async () => {
  await Promise.all([loadData(), loadIndex()]);
  render(store.get());
  refreshBuildings();
});

// test/debug handle
window.__upnext = { map, store, overlay, runtime: () => runtime, cam };
