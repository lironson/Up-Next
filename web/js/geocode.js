// Address -> coordinates via OpenStreetMap Nominatim (free, CORS-enabled).
// Usage policy: max 1 req/s, only on explicit submit, attribution shown in the footer.
const URL_BASE = 'https://nominatim.openstreetmap.org/search';
const VIEWBOX = '-123.27,49.33,-123.02,49.19'; // City of Vancouver (+ a little margin)
let last = 0;

async function query(q, bounded) {
  const wait = 1100 - (Date.now() - last);
  if (wait > 0) await new Promise((r) => setTimeout(r, wait));
  last = Date.now();
  const params = new URLSearchParams({
    q, format: 'jsonv2', limit: '5', countrycodes: 'ca', addressdetails: '0',
    viewbox: VIEWBOX, bounded: bounded ? '1' : '0',
  });
  const r = await fetch(`${URL_BASE}?${params}`, { headers: { 'Accept-Language': 'en' } });
  if (!r.ok) throw new Error(`Geocoder error ${r.status}`);
  return (await r.json()).map((x) => ({ label: shortLabel(x.display_name), lat: Number(x.lat), lon: Number(x.lon) }));
}

// "Royal Bank Tower, 1055, West Georgia Street, Financial District, Downtown, Vancouver, ..." -> "1055 West Georgia Street, Downtown"
function shortLabel(full) {
  const parts = full.split(',').map((s) => s.trim());
  const i = parts.findIndex((s) => /^\d+[A-Za-z]?$/.test(s));
  const core = i >= 0 && parts[i + 1] ? [`${parts[i]} ${parts[i + 1]}`, ...parts.slice(i + 2, i + 4)] : parts.slice(0, 3);
  return core.filter((s) => !/Metro Vancouver|British Columbia|Canada|^V\d/.test(s)).join(', ');
}

export async function geocode(text) {
  const q = text.trim();
  if (!q) return [];
  let res = await query(q, true);
  if (!res.length && !/vancouver/i.test(q)) res = await query(`${q}, Vancouver, BC`, true);
  return res;
}
