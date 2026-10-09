/**
 * رصد - طبقة خطوط الأنابيب.
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { pipelinePopup } from '../popups';

export function buildPipelinesLayer(group, pipelines, { popupCtx }) {
  pipelines.forEach(p => {
    if (!Array.isArray(p.coordinates) || p.coordinates.length < 2) return;
    const color = p.type === 'oil' ? '#fbbf24' : '#60a5fa';
    const line = L.polyline(p.coordinates, {
      color, weight: 3, opacity: 0.8, dashArray: p.status === 'partial' ? '5, 8' : null,
    });
    line.bindPopup(pipelinePopup(p, { ...popupCtx, color }));
    group.addLayer(line);
  });
}
