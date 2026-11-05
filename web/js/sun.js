// Shadow-analysis groundwork. NOT wired to rendering yet.
//
// The future feature will:
//   1. show #time-panel (index.html) with a Jan 1 / Jul 1 toggle + hour slider,
//   2. set state.shadows = { enabled: true, dateId, hour } and state.datetime = dateAt(...),
//   3. effects/index.js returns a deck.gl LightingEffect with a _SunLight({ timestamp }),
//   4. layer factories receive ctx.shadowsEnabled and set `_shadow: true` / material.
// deck.gl's _SunLight computes the sun position itself from timestamp + viewport,
// so sunPosition() below is only needed for UI read-outs (azimuth/altitude labels).

export const TIMEZONE = 'America/Vancouver';

// Only two analysis days are required.
export const SHADOW_DATES = [
  { id: 'winter', label: 'Jan 1', month: 0, day: 1, utcOffsetHours: -8 }, // PST
  { id: 'summer', label: 'Jul 1', month: 6, day: 1, utcOffsetHours: -7 }, // PDT
];

/** Local Vancouver wall-clock time on one of SHADOW_DATES -> absolute Date. */
export function dateAt(dateId, hour, year = new Date().getFullYear()) {
  const d = SHADOW_DATES.find((x) => x.id === dateId) ?? SHADOW_DATES[0];
  const h = Math.floor(hour), m = Math.round((hour - h) * 60);
  return new Date(Date.UTC(year, d.month, d.day, h - d.utcOffsetHours, m));
}

/**
 * Sun position for read-outs. Returns { azimuthDeg, altitudeDeg } or null.
 * TODO(shadows): implement (NOAA solar position algorithm) when the feature starts.
 */
export function sunPosition(_date, _lat, _lon) {
  return null;
}
