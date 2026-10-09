/**
 * رصد - طبقة الأحداث: علامة لكل حدث منفرد ودائرة تجميع لكل مجموعة.
 *
 * تبني العلامات في `group` (L.layerGroup) من البيانات وحدها؛ الجاهزية والإظهار
 * وتواقيع المحتوى (تخطّي إعادة البناء) في تأثيرات `RasadMap`.
 */
import L from 'leaflet';
import { THEME, categoryOf, riskColor } from '../../../utils/constants';
import { iconSvg } from '../../../utils/icons';
import { clusterPopup, eventPopup } from '../popups';
import { CLUSTER_PX, NO_NUDGE, Z_OFFSET } from './shared';

const NUCLEAR_CATEGORIES = new Set(['nuclear', 'radiological']);
const THEME_BG = THEME.bg;

/** `getMap`: الخريطة تُقرأ عند النقر لا عند البناء. */
export function buildEventsLayer(group, { events, clusters, nudges, zoomLevel }, { popupCtx, onSelectEvent, getMap }) {
  clusters.forEach((cluster, ci) => {
    const { dx, dy } = nudges.get(`ev:${ci}`) || NO_NUDGE;
    if (cluster.events.length === 1) {
      const ev = cluster.events[0];
      const cat = categoryOf(ev.category);
      const approx = ev.geo_precision === 'country' ? 'approx' : '';
      const critical = ev.severity === 'critical' ? 'critical' : '';
      // iconAnchor مُزاح: العلامة تُرسم بعيداً عن نقطتها بمقدار (dx,dy) بكسل
      // فتظهر بجانب العلامات المتطابقة الموقع بدل الاختفاء تحتها،
      // وpopupAnchor يتبعها كي تبقى النافذة ملتصقة بالعلامة المرئية.
      let sz;
      let html;
      if (NUCLEAR_CATEGORIES.has(ev.category)) {
        // الخبر النووي/الإشعاعي: أيقونة تصنيفه داخل قرص بلون درجة خطره
        sz = ev.severity === 'critical' ? 26 : ev.severity === 'high' ? 22 : 18;
        const rc = riskColor(ev.risk_score);
        html = `<div class="event-marker ${critical} ${approx}" style="width:${sz}px;height:${sz}px;display:flex;align-items:center;justify-content:center;background:${THEME_BG};border-color:${rc};box-shadow:0 0 ${sz}px ${rc}55;">${iconSvg(cat.icon, { size: sz - 10, color: rc, strokeWidth: 2.25 })}</div>`;
      } else {
        sz = ev.severity === 'critical' ? 14 : ev.severity === 'high' ? 11 : 8;
        html = `<div class="event-marker ${critical} ${approx}" style="width:${sz}px;height:${sz}px;background:${cat.color};border-color:${cat.color};"></div>`;
      }
      const icon = L.divIcon({
        className: '', iconSize: [sz, sz],
        iconAnchor: [sz / 2 - dx, sz / 2 - dy],
        popupAnchor: [dx, dy - sz / 2],
        html,
      });
      const m = L.marker([ev.latitude, ev.longitude], { icon, zIndexOffset: Z_OFFSET.event })
        .bindPopup(eventPopup(ev, popupCtx), { maxWidth: 280 });
      m.on('click', () => onSelectEvent?.(ev));
      group.addLayer(m);
    } else {
      // مجموعة نقاط — دائرة تجميع
      const count = cluster.events.length;
      const hasCritical = cluster.events.some(e => e.severity === 'critical' || e.severity === 'high');
      const hasNuclear = cluster.events.some(e => NUCLEAR_CATEGORIES.has(e.category));
      const color = hasCritical ? '#f4585d' : hasNuclear ? '#f2c230' : '#67e8f9';
      const sz = Math.min(20 + count * 2, 44);
      const icon = L.divIcon({
        className: '', iconSize: [sz, sz],
        iconAnchor: [sz / 2 - dx, sz / 2 - dy],
        popupAnchor: [dx, dy - sz / 2],
        html: `<div style="width:${sz}px;height:${sz}px;background:${color}30;border:2px solid ${color};border-radius:50%;display:flex;align-items:center;justify-content:center;color:${color};font-weight:700;font-size:${sz > 30 ? 13 : 11}px;font-family:monospace;box-shadow:0 0 12px ${color}50;cursor:pointer">${count}</div>`,
      });

      const m = L.marker([cluster.lat, cluster.lng], { icon, zIndexOffset: Z_OFFSET.event })
        .bindPopup(clusterPopup(cluster, popupCtx), { maxWidth: 300 });

      // تفويض حدث واحد على عنصر الـ popup نفسه (بدل مستمعات عامة على المستند
      // تتراكم عند كل فتح) — يُنظَّف تلقائياً مع إزالة الـ popup.
      m.on('popupopen', (e) => {
        const root = e.popup.getElement();
        if (!root || root.dataset.rsdBound) return;  // لا نُكرّر الربط عند إعادة الفتح
        root.dataset.rsdBound = '1';
        const activate = (target) => {
          const item = target.closest('.rasad-cluster-item');
          if (!item) return;
          const id = parseInt(item.dataset.id, 10);
          const found = events.find(x => x.id === id);
          if (found) onSelectEvent?.(found);
        };
        root.addEventListener('click', (ev2) => activate(ev2.target));
        root.addEventListener('keydown', (ev2) => {
          if (ev2.key === 'Enter' || ev2.key === ' ') {
            ev2.preventDefault();
            activate(ev2.target);
          }
        });
      });

      // نقرّب فقط إن كان التقريب سيفكّ المجموعة فعلاً (نقاط متباعدة)؛ الأحداث
      // متطابقة الإحداثيات لا يفكّها أي تقريب فتبقى قائمتها المنبثقة هي الواجهة.
      m.on('click', () => {
        const willSplit = cluster.spreadPx * 4 > CLUSTER_PX;
        const map = getMap();
        if (map && willSplit && zoomLevel < 17) {
          map.flyTo([cluster.lat, cluster.lng], zoomLevel + 2, { duration: 0.5 });
        }
      });

      group.addLayer(m);
    }
  });
}
