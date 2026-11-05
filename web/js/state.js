// Single app store + URL-hash persistence. Everything the renderer needs lives here,
// so future features (shadow analysis) only add keys, never new plumbing.

export const STAGES = [
  'Application', 'Under Review', 'Approved', 'Issued',
  'Under Construction', 'Completed', 'Refused/Withdrawn',
];

// RGB per stage (alpha applied by the layer).
export const STAGE_COLORS = {
  'Application':        [158, 112, 230],
  'Under Review':       [ 66, 145, 245],
  'Approved':           [245, 166,  35],
  'Issued':             [232,  76,  61],
  'Under Construction': [220,  40, 120],
  'Completed':          [ 60, 170, 110],
  'Refused/Withdrawn':  [130, 130, 130],
};

export const DEFAULT_FILTERS = {
  stages: ['Approved', 'Issued', 'Under Construction'],
  yearMin: null,      // null = no bound
  yearMax: null,
  minStoreys: 5,      // product focus: > 4 storeys
};

export const VANCOUVER = { lon: -123.1207, lat: 49.2827 };

export function createStore(initial) {
  let state = initial;
  const subs = new Set();
  return {
    get: () => state,
    set(patch) {
      state = { ...state, ...(typeof patch === 'function' ? patch(state) : patch) };
      subs.forEach((fn) => fn(state));
    },
    subscribe(fn) { subs.add(fn); return () => subs.delete(fn); },
  };
}

export function initialState() {
  return {
    address: null,                 // { label, lat, lon }
    filters: { ...DEFAULT_FILTERS },
    layers: { existing: true, developments: true, viewCones: true },
    // --- shadow analysis groundwork (unused until that feature ships) ---
    datetime: null,                // Date; set by the future time panel
    shadows: { enabled: false, dateId: 'summer', hour: 12 },
    // data
    developments: [],              // normalized features
    meta: null,
    ...readHash(),
  };
}

// ---- URL hash: #a=<label>&lat=..&lon=..&s=Approved,Issued&y=2015-2026&f=5
export function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const out = {};
  const filters = { ...DEFAULT_FILTERS };
  if (p.has('s')) filters.stages = p.get('s').split(',').filter((s) => STAGES.includes(s));
  if (p.has('y')) {
    const [a, b] = p.get('y').split('-').map((v) => (v ? Number(v) : null));
    filters.yearMin = Number.isFinite(a) ? a : null;
    filters.yearMax = Number.isFinite(b) ? b : null;
  }
  if (p.has('f')) filters.minStoreys = Math.max(1, Number(p.get('f')) || DEFAULT_FILTERS.minStoreys);
  out.filters = filters;
  const lat = Number(p.get('lat')), lon = Number(p.get('lon'));
  if (Number.isFinite(lat) && Number.isFinite(lon) && p.has('lat')) {
    out.address = { label: p.get('a') || `${lat.toFixed(5)}, ${lon.toFixed(5)}`, lat, lon };
  }
  return out;
}

export function writeHash(state) {
  const p = new URLSearchParams();
  const f = state.filters;
  if (state.address) {
    p.set('a', state.address.label);
    p.set('lat', state.address.lat.toFixed(6));
    p.set('lon', state.address.lon.toFixed(6));
  }
  p.set('s', f.stages.join(','));
  if (f.yearMin != null || f.yearMax != null) p.set('y', `${f.yearMin ?? ''}-${f.yearMax ?? ''}`);
  p.set('f', String(f.minStoreys));
  const next = '#' + p.toString();
  if (next !== location.hash) history.replaceState(null, '', next);
}

export function applyFilters(features, f) {
  const stages = new Set(f.stages);
  return features.filter((ft) => {
    const p = ft.properties;
    if (!stages.has(p.stage)) return false;
    if ((p.storeys ?? 0) < f.minStoreys) return false;
    if (f.yearMin != null && (p.year == null || p.year < f.yearMin)) return false;
    if (f.yearMax != null && (p.year == null || p.year > f.yearMax)) return false;
    return true;
  });
}
