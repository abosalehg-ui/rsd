/**
 * رصد - طبقة القواعد العسكرية.
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { esc } from '../../../utils/security';
import { iconSvg } from '../../../utils/icons';
import { basePopup } from '../popups';
import { NO_NUDGE, Z_OFFSET } from './shared';

export function buildBasesLayer(group, { militaryBases, nudges }, { popupCtx }) {
  militaryBases.forEach((b, bi) => {
    if (typeof b.latitude !== 'number' || typeof b.longitude !== 'number') return;
    const { dx, dy } = nudges.get(`ba:${b.id ?? bi}`) || NO_NUDGE;
    const typeIcon = iconSvg(b.type === 'naval' ? 'anchor' : b.type === 'air' ? 'plane' : 'shield', { size: 11, color: '#c4b5fd' });
    const icon = L.divIcon({
      className: '',
      iconSize: [18, 18],
      iconAnchor: [9 - dx, 9 - dy],
      popupAnchor: [dx, dy - 9],
      html: `<div title="${esc(b.name_ar || b.name_en || '')}" style="width:18px;height:18px;background:rgba(167,139,250,0.15);border:1.5px solid #a78bfa;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:11px;box-shadow:0 0 6px rgba(167,139,250,0.4)">${typeIcon}</div>`,
    });
    const m = L.marker([b.latitude, b.longitude], { icon, zIndexOffset: Z_OFFSET.base })
      .bindPopup(basePopup(b, popupCtx), { maxWidth: 280 });
    group.addLayer(m);
  });
}
