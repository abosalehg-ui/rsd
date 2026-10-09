/**
 * رصد - الخريطة التفاعلية
 *
 * كل نصوص النوافذ تأتي من i18next، واتجاه النافذة يتبع لغة الواجهة.
 * كل قيمة تأتي من مصدر خارجي تمرّ عبر esc()/safeUrl() قبل الحقن.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORIES, timeAgo } from '../../utils/constants';
import { Icon } from '../../utils/icons';
import { CLUSTER_PX, Z_OFFSET } from './layers/shared';
import { buildEventsLayer } from './layers/events';
import { buildFlightsLayer } from './layers/flights';
import { buildIranLayer } from './layers/iran';
import { buildNuclearLayer } from './layers/nuclear';
import { buildBasesLayer } from './layers/bases';
import { buildPipelinesLayer } from './layers/pipelines';
import { buildZonesLayer } from './layers/zones';
import { ZoomIn, ZoomOut, Crosshair, Clock } from 'lucide-react';
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
// المسافة بالبكسل على الشاشة لا بالدرجات: التجميع بالدرجات يترك نقاطاً
// متجاورة تتراكب بصرياً في كل مستويات التقريب فيتعذّر الضغط على حدث بعينه.
// الإسقاط عبر EPSG3857 يجعل العتبة ثابتة بصرياً، وتنفكّ المجموعات تلقائياً
// كلما كبّر المستخدم وتباعدت النقاط على الشاشة. العتبة `CLUSTER_PX` في
// `layers/shared.js` لأن طبقة الأحداث تحكم بها أيضًا هل يفكّ التقريب المجموعة.
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

// ترتيب الرسم في Leaflet (مُعاد تصديره للاختبارات)
export { Z_OFFSET };

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

/**
 * شارة الطيران: العدد الكلي والعسكري، وعند `stale` (آخر جمع فشل) أيقونة ساعة
 * كهرمانية بوقت آخر لقطة ناجحة — كي لا تُقرأ طائرات عمرها دقائق كأنها لحظية.
 */
export function FlightsBadge({ flights, t }) {
  const stale = Boolean(flights.stale);
  const staleTitle = stale ? t('map.flightsStale', { time: timeAgo(flights.updated_at, t) || '—' }) : t('map.flightsLive');
  return (
    <div
      className={`absolute top-3 end-3 z-[1000] bg-rasad-panel/95 border rounded-lg px-2.5 py-1.5 text-xs flex gap-3 ${stale ? 'border-amber-400/60' : 'border-rasad-border'}`}
      title={staleTitle}
      role="status"
    >
      {stale && <Clock className="w-3.5 h-3.5 text-amber-300" aria-hidden="true" />}
      <span className="inline-flex items-center gap-1 text-slate-200"><Icon name="plane" className="w-3.5 h-3.5" /> <span className="font-mono text-white">{flights.total || 0}</span></span>
      <span className="inline-flex items-center gap-1 text-purple-300"><Icon name="shield" className="w-3.5 h-3.5" /> <span className="font-mono text-purple-200">{flights.military || 0}</span></span>
      <span className="sr-only">{staleTitle}</span>
    </div>
  );
}

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

    buildEventsLayer(markersRef.current, { events, clusters, nudges, zoomLevel }, {
      popupCtx, onSelectEvent, getMap: () => mapInstance.current,
    });
  }, [events, clusters, nudges, nudgeSig, showEvents, ready, zoomLevel, onSelectEvent, popupCtx]);

  // ===== طبقة الطيران =====
  useEffect(() => {
    if (!ready || !flightsRef.current) return;
    flightsRef.current.clearLayers();
    if (!showFlights || !flights?.flights) return;
    buildFlightsLayer(flightsRef.current, flights, { popupCtx });
  }, [flights, showFlights, ready, popupCtx]);

  // ===== طبقة أحداث إيران OSINT =====
  useEffect(() => {
    if (!ready || !iranRef.current) return;

    const sig = `${showIran}#${nudgeSig}#${iranStrikes.map(s => `${s.id}:${s.confidence}`).join('|')}`;
    if (sig === iranSigRef.current) return;
    iranSigRef.current = sig;

    iranRef.current.clearLayers();
    if (!showIran) return;

    buildIranLayer(iranRef.current, { iranStrikes, nudges }, { popupCtx, onSelectEvent });
  }, [iranStrikes, nudges, nudgeSig, showIran, ready, onSelectEvent, popupCtx]);

  // ===== طبقة المنشآت النووية ☢️ =====
  useEffect(() => {
    if (!ready || !nuclearRef.current) return;
    nuclearRef.current.clearLayers();
    if (!showNuclear) return;

    buildNuclearLayer(nuclearRef.current, { nuclearFacilities, nudges }, { popupCtx });
  }, [nuclearFacilities, nudges, showNuclear, ready, popupCtx]);

  // ===== طبقة القواعد العسكرية ⚔️ =====
  useEffect(() => {
    if (!ready || !basesRef.current) return;
    basesRef.current.clearLayers();
    if (!showBases) return;
    buildBasesLayer(basesRef.current, { militaryBases, nudges }, { popupCtx });
  }, [militaryBases, nudges, showBases, ready, popupCtx]);

  // ===== طبقة خطوط الأنابيب 🛢️ =====
  useEffect(() => {
    if (!ready || !pipelinesRef.current) return;
    pipelinesRef.current.clearLayers();
    if (!showPipelines) return;
    buildPipelinesLayer(pipelinesRef.current, pipelines, { popupCtx });
  }, [pipelines, showPipelines, ready, popupCtx]);

  // ===== مسافات التخطيط للطوارئ حول محطات القوى =====
  // دوائر متقطّعة باهتة (5/30/100/300 كم) — مرجعية IAEA EPR-NPP لا مناطق
  // معتمدة. تُرسم للمحطات العاملة وقيد الإنشاء فقط.
  useEffect(() => {
    if (!ready || !zonesRef.current) return;
    zonesRef.current.clearLayers();
    if (!showZones) return;
    buildZonesLayer(zonesRef.current, nuclearFacilities);
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
        <FlightsBadge flights={flights} t={t} />
      )}
    </div>
  );
}
