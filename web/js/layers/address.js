// The searched address: a pulsing-ish disc + vertical "eye" mast at ~typical unit height.
export function addressLayer(address) {
  if (!address) return null;
  const d = [{ position: [address.lon, address.lat] }];
  return [
    new deck.ScatterplotLayer({
      id: 'address-disc',
      data: d,
      getPosition: (x) => x.position,
      getRadius: 18,
      radiusUnits: 'meters',
      getFillColor: [20, 120, 255, 90],
      stroked: true,
      getLineColor: [20, 120, 255, 255],
      lineWidthMinPixels: 2,
    }),
  ];
}
