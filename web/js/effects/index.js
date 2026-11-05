// Effect registry: buildEffects(state) -> deck.gl effects array.
// Shadow hook: when state.shadows.enabled, return
//   [new deck.LightingEffect({
//      ambient: new deck.AmbientLight({ intensity: 1.0 }),
//      sun: new deck._SunLight({ timestamp: state.datetime.getTime(), intensity: 2, _shadow: true }),
//   })]
// (set effect.shadowColor = [0, 0, 0, 0.5] for shadow opacity).
export function buildEffects(state) {
  if (!state.shadows?.enabled) return [];
  return []; // TODO(shadows)
}
