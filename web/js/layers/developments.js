import { STAGE_COLORS } from '../state.js';

// Point-only records get a square placeholder footprint (side in metres).
const PLACEHOLDER_SIDE_M = 24;

export function squareAround(lon, lat, side = PLACEHOLDER_SIDE_M) {
  const h = side / 2;
  const dLat = h / 111320;
  const dLon = h / (111320 * Math.cos((lat * Math.PI) / 180));
  return [[lon - dLon, lat - dLat], [lon + dLon, lat - dLat], [lon + dLon, lat + dLat], [lon - dLon, lat + dLat], [lon - dLon, lat - dLat]];
}

/** GeoJSON feature -> list of render items (MultiPolygon splits into parts). */
export function toRenderItems(ft) {
  const g = ft.geometry, p = ft.properties;
  const base = { p, placeholder: false };
  if (!g) return [{ ...base, ring: squareAround(p.lon, p.lat), placeholder: true }];
  if (g.type === 'Polygon') return [{ ...base, ring: g.coordinates[0] }];
  if (g.type === 'MultiPolygon') return g.coordinates.map((poly) => ({ ...base, ring: poly[0] }));
  const [lon, lat] = g.type === 'Point' ? g.coordinates : [p.lon, p.lat];
  return [{ ...base, ring: squareAround(lon, lat), placeholder: true }];
}

const color = (d, a) => [...(STAGE_COLORS[d.p.stage] ?? [200, 200, 200]), a];

export function developmentLayers(ctx) {
  const items = ctx.developmentItems ?? [];
  if (!items.length) return null;
  return [
    new deck.PolygonLayer({
      id: 'developments',
      data: items,
      getPolygon: (d) => d.ring,
      extruded: true,
      wireframe: true,
      getElevation: (d) => d.p.height_m ?? (d.p.storeys ?? 5) * 3.2 + 4,
      getFillColor: (d) => color(d, d.placeholder || d.p.height_estimated ? 120 : 180),
      getLineColor: (d) => color(d, 255),
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 110],
      material: { ambient: 0.55, diffuse: 0.6, shininess: 16 },
      updateTriggers: { getFillColor: ctx.version, getElevation: ctx.version },
    }),
  ];
}
