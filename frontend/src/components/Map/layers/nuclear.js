/**
 * رصد - طبقة المنشآت النووية.
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { esc } from '../../../utils/security';
import { iconSvg } from '../../../utils/icons';
import { nuclearPopup } from '../popups';
import { NO_NUDGE, Z_OFFSET } from './shared';

// ===== ألوان أنواع المنشآت النووية (التسميات من i18n) =====
const NUCLEAR_TYPES = {
  power:       { color: '#f2c230' },
  research:    { color: '#22d3ee' },
  enrichment:  { color: '#f97316' },
  conversion:  { color: '#a78bfa' },
  heavy_water: { color: '#38bdf8' },
  fuel:        { color: '#fb7185' },
};

const NUCLEAR_STATUS_COLORS = {
  operational: '#22c55e',
  construction: '#f59e0b',
  planned: '#94a3b8',
  shutdown: '#ef4444',
  modified: '#a78bfa',
};

export function buildNuclearLayer(group, { nuclearFacilities, nudges }, { popupCtx }) {
  nuclearFacilities.forEach((fac, fi) => {
    if (typeof fac.latitude !== 'number' || typeof fac.longitude !== 'number') return;
    const { dx, dy } = nudges.get(`nu:${fac.id ?? fi}`) || NO_NUDGE;
    const typeInfo = NUCLEAR_TYPES[fac.type] || NUCLEAR_TYPES.research;
    const statusColor = NUCLEAR_STATUS_COLORS[fac.status] || '#94a3b8';
    const isOperational = fac.status === 'operational';
    const sz = fac.type === 'power' ? 22 : 18;
    const name = fac.name_ar || fac.name_en || '';

    const pulse = isOperational
      ? `box-shadow:0 0 ${sz}px ${typeInfo.color}80;animation:nuclear-pulse 2.5s ease-in-out infinite;`
      : `box-shadow:0 0 6px ${typeInfo.color}40;opacity:0.7;`;

    const icon = L.divIcon({
      className: '',
      iconSize: [sz + 6, sz + 6],
      iconAnchor: [(sz + 6) / 2 - dx, (sz + 6) / 2 - dy],
      popupAnchor: [dx, dy - (sz + 6) / 2],
      // esc() على سمة title أيضاً
      html: `<div title="${esc(name)}" style="
        width:${sz}px;height:${sz}px;
        background:${typeInfo.color}20;
        border:2px solid ${typeInfo.color};
        border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        ${pulse}
        cursor:pointer;
      ">${iconSvg('radiation', { size: sz - 6, color: typeInfo.color, strokeWidth: 2.25 })}</div>`,
    });

    const m = L.marker([fac.latitude, fac.longitude], { icon, zIndexOffset: Z_OFFSET.nuclear })
      .bindPopup(
        nuclearPopup(fac, { ...popupCtx, typeColor: typeInfo.color, statusColor }),
        { maxWidth: 320 },
      );
    group.addLayer(m);
  });
}
