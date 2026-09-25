/**
 * رصد - الخريطة التفاعلية
 *
 * كل نصوص النوافذ تأتي من i18next، واتجاه النافذة يتبع لغة الواجهة (كان
 * direction:rtl مثبّتاً فتُعرض النوافذ معكوسة في الوضع الإنجليزي).
 * كل قيمة تأتي من مصدر خارجي تمرّ عبر esc()/safeUrl() قبل الحقن.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORIES, CONFIDENCE, IRAN_EVENT_TYPES, categoryOf, riskColor } from '../../utils/constants';
import { esc } from '../../utils/security';
import { Icon, iconSvg } from '../../utils/icons';
import {
  basePopup, clusterPopup, eventPopup, flightPopup,
  iranPopup, nuclearPopup, pipelinePopup,
} from './popups';
import { ZoomIn, ZoomOut, Crosshair } from 'lucide-react';
import LayerToggles from './LayerToggles';

// الخريطة الأساس: Esri World Dark Gray. صارت CARTO (dark_all) تعيد صورة
// «API KEY REQUIRED» بدل البلاطات لطلبات بلا مفتاح (أيلول/سبتمبر 2026)، فبقيت
// الخريطة بلا يابسة ولا حدود. قابلة للاستبدال بـ VITE_TILE_URL (مع تحديث
// img-src في سياسات CSP الثلاث).
const TILE_URL = import.meta.env.VITE_TILE_URL
  || 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}';
const TILE_ATTRIBUTION = import.meta.env.VITE_TILE_ATTRIBUTION
  || 'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors';

const ME_CENTER = [29.0, 42.0];
const ME_ZOOM = 5;

// 44×44 = الحد الأدنى الموصى به لمساحة اللمس
const CONTROL_BTN =
  'w-11 h-11 bg-rasad-panel border border-rasad-border rounded-lg flex items-center justify-center hover:bg-rasad-border text-cyan-300 focus-ring';

// ===== تجميع النقاط القريبة =====
// المسافة بالبكسل على الشاشة لا بالدرجات: التجميع بالدرجات كان يترك نقاطاً
// متجاورة (أقل من درجتين) تتراكب بصرياً في كل مستويات التقريب فيتعذّر الضغط
// على حدث بعينه. الإسقاط عبر EPSG3857 يجعل العتبة ثابتة بصرياً، وتنفكّ
// المجموعات تلقائياً كلما كبّر المستخدم وتباعدت النقاط على الشاشة.
const CLUSTER_PX = 42;

function clusterEvents(events, zoom) {
  const clusters = [];
  events.forEach(ev => {
    if (!ev.latitude || !ev.longitude) return;
    const p = L.CRS.EPSG3857.latLngToPoint(L.latLng(ev.latitude, ev.longitude), zoom);
    let c = clusters.find(k => {
      const n = k.events.length;
      return Math.hypot(k.px / n - p.x, k.py / n - p.y) < CLUSTER_PX;
    });
    if (!c) {
      c = { px: 0, py: 0, lat: 0, lng: 0, minPx: p, maxPx: p, events: [] };
      clusters.push(c);
    }
    c.events.push(ev);
    c.px += p.x; c.py += p.y;
    c.lat += ev.latitude; c.lng += ev.longitude;
    c.minPx = { x: Math.min(c.minPx.x, p.x), y: Math.min(c.minPx.y, p.y) };
    c.maxPx = { x: Math.max(c.maxPx.x, p.x), y: Math.max(c.maxPx.y, p.y) };
  });
  return clusters.map(c => ({
    lat: c.lat / c.events.length,
    lng: c.lng / c.events.length,
    // قطر المجموعة بالبكسل عند مستوى التقريب الحالي — للحكم هل يفيد التقريب في فكّها
    spreadPx: Math.hypot(c.maxPx.x - c.minPx.x, c.maxPx.y - c.minPx.y),
    events: c.events,
  }));
}

// ===== إزاحة العلامات المتراكبة عبر الطبقات =====
// كل طبقة (أحداث / ضربات إيران / منشآت / قواعد) تُبنى في تأثير مستقل ولا ترى
// الأخرى، فعلامتان على الإحداثيات نفسها تُرسمان فوق بعضهما تماماً وتُحجب إحداهما
// عن النقر (انفجار 💥 مغطّى بنقطة حدث مثلاً). نحسب هنا — مرة واحدة لكل الطبقات —
// إزاحة بكسلية صغيرة توزّع المتراكبات على حلقة فتظهر كلها وتُنقر كل واحدة.
const OVERLAP_PX = 26;

// أولوية الظهور: الأعلى يأخذ الموضع الأول في الحلقة ويُرسم فوق غيره
const LAYER_PRIORITY = { iran: 4, nuclear: 3, base: 2, event: 1 };

// ترتيب الرسم في Leaflet — الضربات والمنشآت فوق نقاط الأحداث دائماً
export const Z_OFFSET = { iran: 400, nuclear: 300, base: 200, event: 0, flight: -100 };

export function computeMarkerNudges(items, zoom) {
  const groups = [];
  items.forEach(it => {
    const p = L.CRS.EPSG3857.latLngToPoint(L.latLng(it.lat, it.lng), zoom);
    const grp = groups.find(gp => Math.hypot(gp.x - p.x, gp.y - p.y) < OVERLAP_PX);
    if (grp) grp.items.push(it);
    else groups.push({ x: p.x, y: p.y, items: [it] });
  });

  const out = new Map();
  groups.forEach(gp => {
    if (gp.items.length < 2) return;   // لا تراكب ⇒ لا إزاحة
    const sorted = [...gp.items].sort(
      (a, b) => (LAYER_PRIORITY[b.kind] || 0) - (LAYER_PRIORITY[a.kind] || 0)
    );
    const radius = 13 + sorted.length * 2.4;
    sorted.forEach((it, i) => {
      const angle = (2 * Math.PI * i) / sorted.length - Math.PI / 2;
      out.set(it.key, { dx: Math.cos(angle) * radius, dy: Math.sin(angle) * radius });
    });
  });
  return out;
}

const NO_NUDGE = { dx: 0, dy: 0 };

// ===== ألوان أنواع المنشآت النووية (التسميات من i18n) =====
const NUCLEAR_TYPES = {
  power:       { color: '#f2c230' },
  research:    { color: '#22d3ee' },
  enrichment:  { color: '#f97316' },
  conversion:  { color: '#a78bfa' },
  heavy_water: { color: '#38bdf8' },
  fuel:        { color: '#fb7185' },
};

const NUCLEAR_CATEGORIES = new Set(['nuclear', 'radiological']);
const THEME_BG = '#0b1016';

const NUCLEAR_STATUS_COLORS = {
  operational: '#22c55e',
  construction: '#f59e0b',
  planned: '#94a3b8',
  shutdown: '#ef4444',
  modified: '#a78bfa',
};

export default function RasadMap({
  events = [],
  flights = null,
  iranStrikes = [],
  nuclearFacilities = [],
  militaryBases = [],
  pipelines = [],
  layers = {},
  onLayerChange,
  selectedEvent,
  onSelectEvent,
}) {
  const { t, i18n } = useTranslation();
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef(null);
  const flightsRef = useRef(null);
  const iranRef = useRef(null);
  const nuclearRef = useRef(null);
  const basesRef = useRef(null);
  const pipelinesRef = useRef(null);
  const zonesRef = useRef(null);
  // تواقيع محتوى الطبقات — نتخطّى إعادة البناء حين لا يتغيّر المحتوى فعلاً، كي
  // لا تُدمَّر النوافذ المفتوحة عند كل استطلاع (كل 30 ثانية) بمصفوفة جديدة الهوية.
  const eventsSigRef = useRef('');
  const iranSigRef = useRef('');
  const [ready, setReady] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(ME_ZOOM);

  const dir = i18n.dir();
  const {
    events: showEvents = true,
    flights: showFlights = true,
    iran: showIran = true,
    nuclear: showNuclear = true,
    zones: showZones = true,
    bases: showBases = false,
    pipelines: showPipelines = false,
  } = layers;

  // قوالب النوافذ في `./popups` — دوال نقيّة تأخذ (البيانات، {t, dir})
  const popupCtx = useMemo(() => ({ t, dir, lang: i18n.language }), [t, dir, i18n.language]);

  useEffect(() => {
    if (mapInstance.current || !mapRef.current) return undefined;
    const map = L.map(mapRef.current, {
      // نُبقي عنصر الإسناد (تتطلّبه شروط OSM/CARTO) لكن مُصغّراً
      center: ME_CENTER, zoom: ME_ZOOM, zoomControl: false,
    });
    L.tileLayer(TILE_URL, {
      maxZoom: 16,
      attribution: TILE_ATTRIBUTION,
    }).addTo(map);
    markersRef.current = L.layerGroup().addTo(map);
    flightsRef.current = L.layerGroup().addTo(map);
    iranRef.current = L.layerGroup().addTo(map);
    nuclearRef.current = L.layerGroup().addTo(map);
    basesRef.current = L.layerGroup().addTo(map);
    pipelinesRef.current = L.layerGroup().addTo(map);
    // الدوائر في overlayPane تحت markerPane دائمًا، وهي غير تفاعلية فلا تحجب النقر
    zonesRef.current = L.layerGroup().addTo(map);
    mapInstance.current = map;
    setReady(true);
    map.on('zoomend', () => setZoomLevel(map.getZoom()));

    // Leaflet لا يلاحظ تغيّر حجم حاويته (طيّ اللوحة/تبديل الجوال) فتبقى بلاطات
    // رمادية ومركز منزاح حتى يتحرّك المستخدم. نراقب الحاوية ونُبطل الحجم.
    let ro;
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => map.invalidateSize());
      ro.observe(mapRef.current);
    }
    return () => {
      if (ro) ro.disconnect();
      map.remove();
      mapInstance.current = null;
    };
  }, []);

  // التجميع مرفوع خارج تأثير الأحداث كي يشارك في حساب الإزاحة عبر الطبقات
  const clusters = useMemo(
    () => (showEvents ? clusterEvents(events, zoomLevel) : []),
    [events, showEvents, zoomLevel]
  );

  const nudges = useMemo(() => {
    const items = [];
    clusters.forEach((c, i) => items.push({ key: `ev:${i}`, kind: 'event', lat: c.lat, lng: c.lng }));
    if (showIran) {
      iranStrikes.forEach((s, i) => {
        if (s.latitude && s.longitude) items.push({ key: `ir:${s.id ?? i}`, kind: 'iran', lat: s.latitude, lng: s.longitude });
      });
    }
    if (showNuclear) {
      nuclearFacilities.forEach((f, i) => {
        if (typeof f.latitude === 'number' && typeof f.longitude === 'number') items.push({ key: `nu:${f.id ?? i}`, kind: 'nuclear', lat: f.latitude, lng: f.longitude });
      });
    }
    if (showBases) {
      militaryBases.forEach((b, i) => {
        if (typeof b.latitude === 'number' && typeof b.longitude === 'number') items.push({ key: `ba:${b.id ?? i}`, kind: 'base', lat: b.latitude, lng: b.longitude });
      });
    }
    return computeMarkerNudges(items, zoomLevel);
    // الطيران مستثنى: يتحرّك كل 30 ثانية فتصير الإزاحة مهتزّة، ويكفيه ترتيب
    // رسم أدنى كي لا يغطي الضربات والمنشآت.
  }, [clusters, iranStrikes, nuclearFacilities, militaryBases, showIran, showNuclear, showBases, zoomLevel]);

  // توقيع الإزاحات — جزء من تواقيع الطبقات كي تُعاد البناء عند تغيّرها
  const nudgeSig = useMemo(
    () => [...nudges].map(([k, v]) => `${k}:${v.dx.toFixed(1)},${v.dy.toFixed(1)}`).join('|'),
    [nudges]
  );

  // معالجات أزرار التحكّم — داخل useCallback كي لا نقرأ الـ ref أثناء العرض
  const zoomIn = useCallback(() => mapInstance.current?.zoomIn(), []);
  const zoomOut = useCallback(() => mapInstance.current?.zoomOut(), []);
  const recenter = useCallback(
    () => mapInstance.current?.flyTo(ME_CENTER, ME_ZOOM, { duration: 0.5 }),
    []
  );

  // ===== طبقة الأحداث =====
  useEffect(() => {
    if (!ready || !markersRef.current) return;

    // توقيع محتوى الطبقة — إن لم يتغيّر (استطلاع أعاد نفس البيانات) لا نعيد البناء
    // فتبقى النافذة المفتوحة حيّة. التكبير يغيّر التجميع فهو جزء من التوقيع.
    const sig = `${showEvents}#${zoomLevel}#${nudgeSig}#${events.map(e => `${e.id}:${e.severity}`).join('|')}`;
    if (sig === eventsSigRef.current) return;
    eventsSigRef.current = sig;

    markersRef.current.clearLayers();
    if (!showEvents) return;

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
        markersRef.current.addLayer(m);
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
          if (mapInstance.current && willSplit && zoomLevel < 17) {
            mapInstance.current.flyTo([cluster.lat, cluster.lng], zoomLevel + 2, { duration: 0.5 });
          }
        });

        markersRef.current.addLayer(m);
      }
    });
  }, [events, clusters, nudges, nudgeSig, showEvents, ready, zoomLevel, onSelectEvent, popupCtx]);

  // ===== طبقة الطيران =====
  useEffect(() => {
    if (!ready || !flightsRef.current) return;
    flightsRef.current.clearLayers();
    if (!showFlights || !flights?.flights) return;
    flights.flights.forEach(f => {
      if (!f.latitude || !f.longitude) return;
      const isMil = f.is_military;
      const sz = isMil ? 18 : 10;
      const icon = L.divIcon({
        className: '', iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
        // أيقونة plane في lucide تتجه 45° — نطرحها كي يطابق الاتجاه المسار
        html: `<div style="transform:rotate(${(Number(f.heading) || 0) - 45}deg);display:flex;opacity:${isMil ? 1 : 0.7}">${iconSvg('plane', { size: sz, color: isMil ? '#c4b5fd' : '#94a3b8' })}</div>`,
      });
      // ترتيب رسم أدنى: الطائرات لا تحجب الضربات والمنشآت الثابتة
      L.marker([f.latitude, f.longitude], { icon, zIndexOffset: Z_OFFSET.flight })
        .bindPopup(flightPopup(f, popupCtx))
        .addTo(flightsRef.current);
    });
  }, [flights, showFlights, ready, popupCtx]);

  // ===== طبقة أحداث إيران OSINT =====
  useEffect(() => {
    if (!ready || !iranRef.current) return;

    const sig = `${showIran}#${nudgeSig}#${iranStrikes.map(s => `${s.id}:${s.confidence}`).join('|')}`;
    if (sig === iranSigRef.current) return;
    iranSigRef.current = sig;

    iranRef.current.clearLayers();
    if (!showIran) return;

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
      iranRef.current.addLayer(m);
    });
  }, [iranStrikes, nudges, nudgeSig, showIran, ready, onSelectEvent, popupCtx]);

  // ===== طبقة المنشآت النووية ☢️ =====
  useEffect(() => {
    if (!ready || !nuclearRef.current) return;
    nuclearRef.current.clearLayers();
    if (!showNuclear) return;

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
        // esc() على سمة title أيضاً — كانت الوحيدة غير المهرَّبة في الملف
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
      nuclearRef.current.addLayer(m);
    });
  }, [nuclearFacilities, nudges, showNuclear, ready, popupCtx]);

  // ===== طبقة القواعد العسكرية ⚔️ =====
  useEffect(() => {
    if (!ready || !basesRef.current) return;
    basesRef.current.clearLayers();
    if (!showBases) return;
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
      basesRef.current.addLayer(m);
    });
  }, [militaryBases, nudges, showBases, ready, popupCtx]);

  // ===== طبقة خطوط الأنابيب 🛢️ =====
  useEffect(() => {
    if (!ready || !pipelinesRef.current) return;
    pipelinesRef.current.clearLayers();
    if (!showPipelines) return;
    pipelines.forEach(p => {
      if (!Array.isArray(p.coordinates) || p.coordinates.length < 2) return;
      const color = p.type === 'oil' ? '#fbbf24' : '#60a5fa';
      const line = L.polyline(p.coordinates, {
        color, weight: 3, opacity: 0.8, dashArray: p.status === 'partial' ? '5, 8' : null,
      });
      line.bindPopup(pipelinePopup(p, { ...popupCtx, color }));
      pipelinesRef.current.addLayer(line);
    });
  }, [pipelines, showPipelines, ready, popupCtx]);

  // ===== مسافات التخطيط للطوارئ حول محطات القوى =====
  // دوائر متقطّعة باهتة (5/30/100/300 كم) — مرجعية IAEA EPR-NPP لا مناطق
  // معتمدة. تُرسم للمحطات العاملة وقيد الإنشاء فقط.
  useEffect(() => {
    if (!ready || !zonesRef.current) return;
    zonesRef.current.clearLayers();
    if (!showZones) return;
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
        zonesRef.current.addLayer(circle);
      });
      // تسمية واحدة على الدائرة الأكبر
      const outer = fac.planning_zones[fac.planning_zones.length - 1];
      const labelLat = fac.latitude + (outer.km / 111);
      zonesRef.current.addLayer(L.marker([labelLat, fac.longitude], {
        interactive: false,
        icon: L.divIcon({
          className: '',
          iconSize: [80, 14],
          iconAnchor: [40, 7],
          html: `<div dir="ltr" style="font:10px 'IBM Plex Mono',monospace;color:#f2c230aa;text-align:center">${esc(outer.key)} ${esc(outer.km)} km</div>`,
        }),
      }));
    });
  }, [nuclearFacilities, showZones, ready]);

  useEffect(() => {
    if (selectedEvent?.latitude && mapInstance.current) {
      mapInstance.current.flyTo([selectedEvent.latitude, selectedEvent.longitude], 8, { duration: 1 });
    }
  }, [selectedEvent]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />

      <div className="absolute top-3 start-3 z-[1000] flex flex-col gap-2">
        <button onClick={zoomIn} aria-label={t('map.zoomIn')} title={t('map.zoomIn')} className={CONTROL_BTN}>
          <ZoomIn className="w-5 h-5" aria-hidden="true" />
        </button>
        <button onClick={zoomOut} aria-label={t('map.zoomOut')} title={t('map.zoomOut')} className={CONTROL_BTN}>
          <ZoomOut className="w-5 h-5" aria-hidden="true" />
        </button>
        <button onClick={recenter} aria-label={t('map.recenter')} title={t('map.recenter')} className={CONTROL_BTN}>
          <Crosshair className="w-5 h-5" aria-hidden="true" />
        </button>
      </div>

      <LayerToggles
        layers={layers}
        onLayerChange={onLayerChange}
        className="absolute bottom-3 start-3 z-[1000] max-w-[45vw]"
      />

      <div className="absolute bottom-3 end-3 z-[1000] bg-rasad-panel/95 border border-rasad-border rounded-lg p-3 hidden sm:block">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          {Object.entries(CATEGORIES).map(([k, c]) => (
            <div key={k} className="flex items-center gap-1.5">
              <Icon name={c.icon} className="w-3.5 h-3.5" style={{ color: c.color }} />
              <span className="text-xs text-slate-200">{t(`categories.${k}`)}</span>
            </div>
          ))}
        </div>
        <p className="mt-2 pt-2 border-t border-rasad-border text-2xs text-slate-400">{t('map.approx')}</p>
        {showZones && <p className="text-2xs text-hazard-soft/80 max-w-[15rem]">{t('map.zonesNote')}</p>}
      </div>

      {flights && showFlights && (
        <div className="absolute top-3 end-3 z-[1000] bg-rasad-panel/95 border border-rasad-border rounded-lg px-2.5 py-1.5 text-xs flex gap-3">
          <span className="inline-flex items-center gap-1 text-slate-200"><Icon name="plane" className="w-3.5 h-3.5" /> <span className="font-mono text-white">{flights.total || 0}</span></span>
          <span className="inline-flex items-center gap-1 text-purple-300"><Icon name="shield" className="w-3.5 h-3.5" /> <span className="font-mono text-purple-200">{flights.military || 0}</span></span>
        </div>
      )}
    </div>
  );
}
