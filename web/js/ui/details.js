// Click/hover details for picked objects.
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function developmentHtml(p) {
  const h = p.height_m != null ? `${Math.round(p.height_m)} m${p.height_estimated ? ' <em>(est.)</em>' : ''}` : '—';
  const rows = [
    ['Stage', `${esc(p.stage)}${p.stage_raw && p.stage_raw !== p.stage ? ` <span class="muted">(${esc(p.stage_raw)})</span>` : ''}`],
    ['Storeys', esc(p.storeys ?? '—')],
    ['Height', h],
    ['Year', esc(p.year ?? '—')],
    ['Use', esc(p.use || '—')],
    ['Footprint', p.footprint_source?.startsWith('parcel') ? 'Lot outline (building may be smaller)' : 'Approximate (location only)'],
    ['Source', esc(p.source)],
  ];
  return `<div class="pop">
    <h3>${esc(p.address || 'Unknown address')}</h3>
    <table>${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('')}</table>
    ${p.description ? `<p class="desc">${esc(p.description)}</p>` : ''}
    ${p.url ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">View permit record ↗</a>` : ''}
  </div>`;
}

export function tooltip({ object, layer }) {
  if (!object || !layer) return null;
  if (layer.id === 'existing-buildings') return { text: `Existing building · ${Math.round(object.h)} m` };
  if (layer.id === 'view-cones') return { text: `Protected view ${object.properties.view_number}: ${object.properties.name}\n${object.properties.description || ''}` };
  if (layer.id === 'developments') {
    const p = object.p;
    return { text: `${p.address}\n${p.stage} · ${p.storeys ?? '?'} storeys${p.year ? ' · ' + p.year : ''}` };
  }
  return null;
}
