/**
 * رصد - طبقة الطيران الحي.
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { THEME } from '../../../utils/constants';
import { iconSvg } from '../../../utils/icons';
import { flightPopup } from '../popups';
import { Z_OFFSET } from './shared';

export function buildFlightsLayer(group, flights, { popupCtx }) {
  flights.flights.forEach(f => {
    if (!f.latitude || !f.longitude) return;
    const isMil = f.is_military;
    // الطوارئ (سكواك 7500/7600/7700) أبرز من العسكري: معلومة OSINT لا تُهدر
    const isEmergency = Boolean(f.is_emergency);
    const sz = isEmergency ? 20 : isMil ? 18 : 10;
    const color = isEmergency ? THEME.emergency : isMil ? THEME.flightMilitary : THEME.flightCivil;
    const icon = L.divIcon({
      className: '', iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
      // أيقونة plane في lucide تتجه 45° — نطرحها كي يطابق الاتجاه المسار
      html: `<div style="transform:rotate(${(Number(f.heading) || 0) - 45}deg);display:flex;opacity:${isMil || isEmergency ? 1 : 0.7};${isEmergency ? `filter:drop-shadow(0 0 6px ${THEME.emergency})` : ''}">${iconSvg('plane', { size: sz, color })}</div>`,
    });
    // ترتيب رسم أدنى: الطائرات لا تحجب الضربات والمنشآت الثابتة
    L.marker([f.latitude, f.longitude], { icon, zIndexOffset: Z_OFFSET.flight })
      .bindPopup(flightPopup(f, popupCtx))
      .addTo(group);
  });
}
