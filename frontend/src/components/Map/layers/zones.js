/**
 * رصد - مسافات التخطيط للطوارئ حول محطات القوى (مرجعية IAEA EPR-NPP).
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { esc } from '../../../utils/security';

export function buildZonesLayer(group, nuclearFacilities) {
  nuclearFacilities.forEach(fac => {
    if (!fac.planning_zones?.length || !['operational', 'construction'].includes(fac.status)) return;
    fac.planning_zones.forEach((z, i) => {
      const circle = L.circle([fac.latitude, fac.longitude], {
        radius: z.km * 1000,
        color: '#f2c230',
        weight: i < 2 ? 1.25 : 1,
        opacity: 0.55 - i * 0.1,
        dashArray: i < 2 ? null : '4 6',
        fill: i === 0,
        fillOpacity: 0.08,
        interactive: false,
      });
      group.addLayer(circle);
    });
    // تسمية واحدة على الدائرة الأكبر
    const outer = fac.planning_zones[fac.planning_zones.length - 1];
    const labelLat = fac.latitude + (outer.km / 111);
    group.addLayer(L.marker([labelLat, fac.longitude], {
      interactive: false,
      icon: L.divIcon({
        className: '',
        iconSize: [80, 14],
        iconAnchor: [40, 7],
        html: `<div dir="ltr" style="font:10px 'IBM Plex Mono',monospace;color:#f2c230aa;text-align:center">${esc(outer.key)} ${esc(outer.km)} km</div>`,
      }),
    }));
  });
}
