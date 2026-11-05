// City of Vancouver protected public view cones (ground overlay).
export function viewConeLayer(ctx) {
  if (!ctx.viewCones?.features?.length) return null;
  return new deck.GeoJsonLayer({
    id: 'view-cones',
    data: ctx.viewCones,
    filled: true,
    stroked: true,
    getFillColor: [0, 150, 160, 28],
    getLineColor: [0, 130, 140, 160],
    lineWidthMinPixels: 1,
    pickable: true,
    parameters: { depthTest: false },
  });
}
