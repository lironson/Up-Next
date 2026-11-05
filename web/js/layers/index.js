import { existingLayer } from './existing.js';
import { developmentLayers } from './developments.js';
import { addressLayer } from './address.js';
import { viewConeLayer } from './viewcones.js';

// Layer registry. Order = draw order. Each entry: build(state, ctx) -> Layer | Layer[] | null.
// ctx carries runtime-only inputs (loaded buildings, filtered features, flags).
const REGISTRY = [
  // Reserved: shadow-receiving ground plane for the future shadow analysis
  // (a SolidPolygonLayer around the address with `_shadow` material). Returns null for now.
  { id: 'ground', build: (state, ctx) => (ctx.shadowsEnabled ? null : null) },
  { id: 'viewCones', build: (state, ctx) => (state.layers.viewCones ? viewConeLayer(ctx) : null) },
  { id: 'existing', build: (state, ctx) => (state.layers.existing ? existingLayer(ctx) : null) },
  { id: 'developments', build: (state, ctx) => (state.layers.developments ? developmentLayers(ctx) : null) },
  { id: 'address', build: (state) => addressLayer(state.address) },
];

export function buildLayers(state, ctx) {
  const full = { ...ctx, shadowsEnabled: !!state.shadows?.enabled };
  return REGISTRY.flatMap((r) => [r.build(state, full)].flat()).filter(Boolean);
}
