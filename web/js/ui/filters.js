import { STAGES, STAGE_COLORS, DEFAULT_FILTERS } from '../state.js';

const rgb = (c) => `rgb(${c.join(',')})`;

/** Render the filter panel once; re-render counts on every state change. */
export function mountFilters(root, store) {
  root.innerHTML = `
    <fieldset class="stages"><legend>Development stage</legend><div id="stage-list"></div>
      <p id="stage-note" class="muted small" hidden></p></fieldset>
    <div class="row">
      <label>Year from <input id="year-min" type="number" inputmode="numeric" placeholder="any"></label>
      <label>to <input id="year-max" type="number" inputmode="numeric" placeholder="any"></label>
    </div>
    <label class="slider">Min. storeys <output id="storeys-out"></output>
      <input id="min-storeys" type="range" min="5" max="60" step="1">
    </label>
    <fieldset class="toggles"><legend>Layers</legend>
      <label><input type="checkbox" id="lyr-existing"> Existing buildings</label>
      <label><input type="checkbox" id="lyr-dev"> New developments</label>
      <label><input type="checkbox" id="lyr-cones"> Protected view cones</label>
    </fieldset>
    <button type="button" id="reset-filters" class="link">Reset filters</button>`;

  const list = root.querySelector('#stage-list');
  list.innerHTML = STAGES.map((s) => `
    <label class="stage"><input type="checkbox" value="${s}">
      <span class="sw" style="background:${rgb(STAGE_COLORS[s])}"></span>
      <span class="name">${s}</span><span class="count" data-stage="${s}"></span></label>`).join('');

  const $ = (id) => root.querySelector(id);
  const setFilters = (patch) => store.set((st) => ({ filters: { ...st.filters, ...patch } }));

  list.addEventListener('change', () => {
    setFilters({ stages: [...list.querySelectorAll('input:checked')].map((i) => i.value) });
  });
  const num = (v) => (v === '' ? null : Number(v));
  $('#year-min').addEventListener('change', (e) => setFilters({ yearMin: num(e.target.value) }));
  $('#year-max').addEventListener('change', (e) => setFilters({ yearMax: num(e.target.value) }));
  $('#min-storeys').addEventListener('input', (e) => setFilters({ minStoreys: Number(e.target.value) }));
  $('#lyr-existing').addEventListener('change', (e) => store.set((st) => ({ layers: { ...st.layers, existing: e.target.checked } })));
  $('#lyr-dev').addEventListener('change', (e) => store.set((st) => ({ layers: { ...st.layers, developments: e.target.checked } })));
  $('#lyr-cones').addEventListener('change', (e) => store.set((st) => ({ layers: { ...st.layers, viewCones: e.target.checked } })));
  $('#reset-filters').addEventListener('click', () => store.set({ filters: { ...DEFAULT_FILTERS } }));

  const sync = (st) => {
    const f = st.filters;
    list.querySelectorAll('input').forEach((i) => { i.checked = f.stages.includes(i.value); });
    $('#year-min').value = f.yearMin ?? '';
    $('#year-max').value = f.yearMax ?? '';
    $('#min-storeys').value = f.minStoreys;
    $('#storeys-out').textContent = `${f.minStoreys}+`;
    $('#lyr-existing').checked = st.layers.existing;
    $('#lyr-dev').checked = st.layers.developments;
    $('#lyr-cones').checked = st.layers.viewCones;
    // counts by stage honouring the other filters (not the stage filter itself)
    const counts = {};
    for (const ft of st.developments) {
      const p = ft.properties;
      if ((p.storeys ?? 0) < f.minStoreys) continue;
      if (f.yearMin != null && (p.year == null || p.year < f.yearMin)) continue;
      if (f.yearMax != null && (p.year == null || p.year > f.yearMax)) continue;
      counts[p.stage] = (counts[p.stage] || 0) + 1;
    }
    list.querySelectorAll('.count').forEach((el) => { el.textContent = counts[el.dataset.stage] || 0; });
    // Stages with no records in the whole dataset: grey out and explain.
    const present = new Set(st.developments.map((ft) => ft.properties.stage));
    list.querySelectorAll('.stage').forEach((row) => {
      const empty = st.developments.length > 0 && !present.has(row.querySelector('input').value);
      row.classList.toggle('empty', empty);
      row.title = empty ? 'No open data source publishes this stage yet' : '';
    });
    const note = root.querySelector('#stage-note');
    note.hidden = !st.developments.length || present.size > 1;
    note.textContent = 'The City of Vancouver currently publishes only issued building permits as open data. Earlier stages (application, review, approval) will appear here when a source is added.';
  };
  store.subscribe(sync);
  sync(store.get());
}

/** Nearby list: filtered developments within radius, sorted by distance. */
export function renderNearby(root, address, items, onPick) {
  if (!address) { root.innerHTML = '<p class="muted">Search an address to list nearby developments.</p>'; return; }
  const R = 2000;
  const near = items
    .map((ft) => ({ ft, d: distM(address, ft.properties) }))
    .filter((x) => x.d <= R)
    .sort((a, b) => a.d - b.d)
    .slice(0, 50);
  if (!near.length) { root.innerHTML = `<p class="muted">No matching developments within ${R / 1000} km.</p>`; return; }
  root.innerHTML = `<p class="muted">${near.length} within ${R / 1000} km</p><ol>${near.map(({ ft, d }, i) => {
    const p = ft.properties;
    return `<li data-i="${i}"><span class="sw" style="background:${rgb(STAGE_COLORS[p.stage] ?? [200, 200, 200])}"></span>
      <span class="addr">${escapeHtml(p.address)}</span>
      <span class="meta">${p.storeys ?? '?'} st · ${p.stage}${p.year ? ' · ' + p.year : ''} · ${fmtDist(d)}</span></li>`;
  }).join('')}</ol>`;
  root.querySelectorAll('li').forEach((li) => li.addEventListener('click', () => onPick(near[Number(li.dataset.i)].ft)));
}

export function distM(a, b) {
  const R = 6371000, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLon = (b.lon - a.lon) * toR;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}
const fmtDist = (d) => (d < 1000 ? `${Math.round(d / 10) * 10} m` : `${(d / 1000).toFixed(1)} km`);
const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
