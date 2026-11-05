// Existing buildings: pre-baked City footprints split into grid chunks (data/buildings/).
// Chunk file format: { "b": [[height_m, [[lon,lat], ...]], ...] }  (outer ring only)
// index.json: { "cell": 0.01, "chunks": ["<gx>_<gy>", ...], "source": "...", "generated_at": "..." }

const BASE = 'data/buildings/';
const MAX_CHUNKS_PER_VIEW = 64;

let index = null;          // Promise<index json | null>
const cache = new Map();   // key -> Promise<array>
let available = new Set();

export function loadIndex() {
  if (!index) {
    index = fetch(BASE + 'index.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => { if (j) available = new Set(j.chunks); return j; })
      .catch(() => null);
  }
  return index;
}

function chunk(key) {
  if (!cache.has(key)) {
    cache.set(key, fetch(`${BASE}${key}.json`)
      .then((r) => (r.ok ? r.json() : { b: [] }))
      .then((j) => j.b.map(([h, ring]) => ({ h, ring })))
      .catch(() => []));
  }
  return cache.get(key);
}

/** Load all chunks intersecting [west, south, east, north]. Returns flat building list. */
export async function loadBuildings(bbox) {
  const idx = await loadIndex();
  if (!idx) return [];
  const c = idx.cell;
  const [w, s, e, n] = bbox;
  const keys = [];
  for (let gx = Math.floor(w / c); gx <= Math.floor(e / c); gx++) {
    for (let gy = Math.floor(s / c); gy <= Math.floor(n / c); gy++) {
      const k = `${gx}_${gy}`;
      if (available.has(k)) keys.push(k);
    }
  }
  if (keys.length > MAX_CHUNKS_PER_VIEW) return null; // too zoomed out; caller keeps what it has
  const parts = await Promise.all(keys.map(chunk));
  return parts.flat();
}

/** bbox of a radius (m) around a point. */
export function bboxAround(lon, lat, radiusM) {
  const dLat = radiusM / 111320;
  const dLon = radiusM / (111320 * Math.cos((lat * Math.PI) / 180));
  return [lon - dLon, lat - dLat, lon + dLon, lat + dLat];
}

export function existingLayer(ctx) {
  if (!ctx.buildings?.length) return null;
  return new deck.PolygonLayer({
    id: 'existing-buildings',
    data: ctx.buildings,
    getPolygon: (d) => d.ring,
    extruded: true,
    wireframe: true,
    filled: true,
    getElevation: (d) => d.h,
    getFillColor: [170, 178, 190, 80],
    getLineColor: [90, 98, 110, 90],
    pickable: true,
    autoHighlight: true,
    highlightColor: [255, 255, 255, 90],
    material: { ambient: 0.6, diffuse: 0.5, shininess: 8 },
    // shadow groundwork: future feature toggles shadow material here via ctx.shadowsEnabled
  });
}
