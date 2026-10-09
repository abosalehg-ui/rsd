/**
 * رصد - طبقة أحداث إيران OSINT.
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { CONFIDENCE, IRAN_EVENT_TYPES } from '../../../utils/constants';
import { iconSvg } from '../../../utils/icons';
import { iranPopup } from '../popups';
import { NO_NUDGE, Z_OFFSET } from './shared';

export function buildIranLayer(group, { iranStrikes, nudges }, { popupCtx, onSelectEvent }) {
  iranStrikes.forEach((strike, si) => {
    if (!strike.latitude || !strike.longitude) return;
    const { dx, dy } = nudges.get(`ir:${strike.id ?? si}`) || NO_NUDGE;
    const conf = CONFIDENCE[strike.confidence] || CONFIDENCE.LOW;
    const evType = IRAN_EVENT_TYPES[strike.event_type] || IRAN_EVENT_TYPES.strike;
    const sz = strike.confidence === 'HIGH' ? 18 : strike.confidence === 'MEDIUM' ? 14 : 10;

    const icon = L.divIcon({
      className: '',
      iconSize: [sz + 8, sz + 8],
      iconAnchor: [(sz + 8) / 2 - dx, (sz + 8) / 2 - dy],
      popupAnchor: [dx, dy - (sz + 8) / 2],
      html: `<div style="
        width:${sz}px;height:${sz}px;
        background:${evType.color}30;
        border:2px solid ${evType.color};
        border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 0 ${sz}px ${conf.color}80;
        position:relative;
      ">
        ${iconSvg(evType.icon, { size: Math.max(sz - 6, 8), color: evType.color })}
        <div style="
          position:absolute;bottom:-4px;inset-inline-end:-4px;
          width:8px;height:8px;
          border-radius:50%;
          background:${conf.color};
          border:1px solid #000;
        "></div>
      </div>`,
    });

    const m = L.marker([strike.latitude, strike.longitude], { icon, zIndexOffset: Z_OFFSET.iran })
      .bindPopup(iranPopup(strike, popupCtx), { maxWidth: 300 });

    m.on('click', () => onSelectEvent?.(strike));
    group.addLayer(m);
  });
}
