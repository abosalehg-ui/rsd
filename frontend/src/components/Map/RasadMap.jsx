/**
 * رصد - الخريطة التفاعلية
 *
 * كل نصوص النوافذ تأتي من i18next، واتجاه النافذة يتبع لغة الواجهة (كان
 * direction:rtl مثبّتاً فتُعرض النوافذ معكوسة في الوضع الإنجليزي).
 * كل قيمة تأتي من مصدر خارجي تمرّ عبر esc()/safeUrl() قبل الحقن.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORIES, COUNTRIES, categoryOf, severityOf, CONFIDENCE, IRAN_EVENT_TYPES, timeAgo } from '../../utils/constants';
import { esc, safeUrl } from '../../utils/security';
import { Layers, ZoomIn, ZoomOut, Crosshair } from 'lucide-react';

const ME_CENTER = [29.0, 42.0];
const ME_ZOOM = 5;

// 44×44 = الحد الأدنى الموصى به لمساحة اللمس
const CONTROL_BTN =
  'w-11 h-11 bg-rasad-panel border border-rasad-border rounded-lg flex items-center justify-center hover:bg-rasad-border text-cyan-300 focus-ring';

// ===== تجميع النقاط القريبة =====
function clusterEvents(events, zoom) {
  const gridSize = Math.max(2, 30 / Math.pow(2, zoom - 3));
  const clusters = {};
  events.forEach(ev => {
    if (!ev.latitude || !ev.longitude) return;
    const key = `${Math.round(ev.latitude / gridSize * 100)}_${Math.round(ev.longitude / gridSize * 100)}`;
    if (!clusters[key]) clusters[key] = { lat: 0, lng: 0, events: [] };
    clusters[key].events.push(ev);
    clusters[key].lat += ev.latitude;
    clusters[key].lng += ev.longitude;
  });
  return Object.values(clusters).map(c => ({
    lat: c.lat / c.events.length,
    lng: c.lng / c.events.length,
    events: c.events,
  }));
}

// ===== ألوان أنواع المنشآت النووية (التسميات من i18n) =====
const NUCLEAR_TYPES = {
  power:       { color: '#facc15', icon: '☢️' },
  research:    { color: '#22d3ee', icon: '⚛️' },
  enrichment:  { color: '#f97316', icon: '☢️' },
  conversion:  { color: '#a78bfa', icon: '⚗️' },
  heavy_water: { color: '#38bdf8', icon: '💧' },
  fuel:        { color: '#fb7185', icon: '⚛️' },
};

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
    bases: showBases = false,
    pipelines: showPipelines = false,
  } = layers;

  /** غلاف موحّد لمحتوى النوافذ — كان القالب مكرّراً في خمسة مواضع. */
  const popupShell = useCallback(
    (inner, minWidth = 220) =>
      `<div style="min-width:${minWidth}px;font-family:Tajawal,sans-serif;direction:${dir}">${inner}</div>`,
    [dir]
  );

  useEffect(() => {
    if (mapInstance.current || !mapRef.current) return undefined;
    const map = L.map(mapRef.current, {
      // نُبقي عنصر الإسناد (تتطلّبه شروط OSM/CARTO) لكن مُصغّراً
      center: ME_CENTER, zoom: ME_ZOOM, zoomControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);
    markersRef.current = L.layerGroup().addTo(map);
    flightsRef.current = L.layerGroup().addTo(map);
    iranRef.current = L.layerGroup().addTo(map);
    nuclearRef.current = L.layerGroup().addTo(map);
    basesRef.current = L.layerGroup().addTo(map);
    pipelinesRef.current = L.layerGroup().addTo(map);
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
    const sig = `${showEvents}#${zoomLevel}#${events.map(e => `${e.id}:${e.severity}`).join('|')}`;
    if (sig === eventsSigRef.current) return;
    eventsSigRef.current = sig;

    markersRef.current.clearLayers();
    if (!showEvents) return;

    const clusters = clusterEvents(events, zoomLevel);

    clusters.forEach(cluster => {
      if (cluster.events.length === 1) {
        const ev = cluster.events[0];
        const cat = categoryOf(ev.category);
        const sev = severityOf(ev.severity);
        const catLabel = t(`categories.${ev.category}`, { defaultValue: t('categories.general') });
        const sevLabel = t(`severity.${ev.severity}`, { defaultValue: t('severity.low') });
        const sz = ev.severity === 'critical' ? 16 : ev.severity === 'high' ? 12 : 9;
        const icon = L.divIcon({
          className: '', iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
          html: `<div class="event-marker ${ev.severity === 'critical' ? 'critical' : ''}" style="width:${sz}px;height:${sz}px;background:${cat.color};border-color:${cat.color};box-shadow:0 0 ${sz}px ${cat.color}40;"></div>`,
        });
        const flag = COUNTRIES[ev.country_code]?.flag || '🌍';
        const link = safeUrl(ev.url);
        const country = t(`countries.${ev.country_code}`, { defaultValue: ev.country || '' });
        const m = L.marker([ev.latitude, ev.longitude], { icon }).bindPopup(popupShell(`
            <div style="display:flex;gap:4px;margin-bottom:6px">
              <span style="font-size:16px">${cat.icon}</span>
              <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${cat.color}20;color:${cat.color}">${esc(catLabel)}</span>
              <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${sev.color}20;color:${sev.color}">${esc(sevLabel)}</span>
            </div>
            <h3 style="font-size:13px;font-weight:700;margin-bottom:4px;line-height:1.5">${esc(ev.title)}</h3>
            <p style="font-size:11px;color:#cbd5e1;margin-bottom:6px">${esc((ev.description || '').substring(0, 100))}</p>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8">
              <span>${flag} ${esc(country)}</span><span>${esc(timeAgo(ev.event_date, t))}</span>
            </div>
            ${link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer" style="display:block;margin-top:6px;font-size:11px;color:#67e8f9">${esc(t('map.sourceLink'))}</a>` : ''}
          `), { maxWidth: 280 });
        m.on('click', () => onSelectEvent?.(ev));
        markersRef.current.addLayer(m);
      } else {
        // مجموعة نقاط — دائرة تجميع
        const count = cluster.events.length;
        const hasCritical = cluster.events.some(e => e.severity === 'critical' || e.severity === 'high');
        const color = hasCritical ? '#ef4444' : '#22d3ee';
        const sz = Math.min(20 + count * 2, 44);
        const icon = L.divIcon({
          className: '', iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
          html: `<div style="width:${sz}px;height:${sz}px;background:${color}30;border:2px solid ${color};border-radius:50%;display:flex;align-items:center;justify-content:center;color:${color};font-weight:700;font-size:${sz > 30 ? 13 : 11}px;font-family:monospace;box-shadow:0 0 12px ${color}50;cursor:pointer">${count}</div>`,
        });

        const listHtml = cluster.events.slice(0, 8).map(ev => {
          const cat = categoryOf(ev.category);
          return `<div class="rasad-cluster-item" data-id="${esc(ev.id)}" tabindex="0" role="button" style="padding:4px 0;border-bottom:1px solid #1e293b;font-size:11px;line-height:1.5;cursor:pointer;color:#cbd5e1">${cat.icon} ${esc((ev.title || '').substring(0, 60))}</div>`;
        }).join('');
        const moreText = count > 8
          ? `<div style="font-size:11px;color:#94a3b8;padding-top:4px">${esc(t('map.clusterMore', { count: count - 8 }))}</div>`
          : '';

        const m = L.marker([cluster.lat, cluster.lng], { icon }).bindPopup(popupShell(`
            <div style="max-height:250px;overflow-y:auto">
              <div style="font-size:12px;font-weight:700;margin-bottom:6px;color:#67e8f9">${esc(t('map.clusterTitle', { count }))}</div>
              ${listHtml}
              ${moreText}
            </div>
          `, 240), { maxWidth: 300 });

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

        m.on('click', () => {
          if (mapInstance.current && zoomLevel < 8) {
            mapInstance.current.flyTo([cluster.lat, cluster.lng], zoomLevel + 2, { duration: 0.5 });
          }
        });

        markersRef.current.addLayer(m);
      }
    });
  }, [events, showEvents, ready, zoomLevel, onSelectEvent, t, popupShell]);

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
        html: `<div style="transform:rotate(${Number(f.heading) || 0}deg);font-size:${sz}px;filter:drop-shadow(0 0 3px ${isMil ? '#a855f7' : '#64748b'})">✈️</div>`,
      });
      L.marker([f.latitude, f.longitude], { icon }).bindPopup(popupShell(`
          <div style="font-weight:700;font-family:monospace">${esc(f.callsign || f.icao24)}</div>
          ${isMil ? `<span style="font-size:11px;color:#c4b5fd">⚔️ ${esc(t('map.military'))}</span>` : ''}
          <div style="font-size:11px;color:#cbd5e1;margin-top:4px">
            ${esc(f.origin_country || '')}<br/>
            ${esc(t('map.altitude'))}: ${f.altitude ? esc(Math.round(f.altitude)) + ' ' + esc(t('map.metersShort')) : '—'}<br/>
            ${esc(t('map.speed'))}: ${f.velocity ? esc(Math.round(f.velocity * 3.6)) + ' ' + esc(t('map.kmhShort')) : '—'}
          </div>
        `, 160)).addTo(flightsRef.current);
    });
  }, [flights, showFlights, ready, t, popupShell]);

  // ===== طبقة أحداث إيران OSINT =====
  useEffect(() => {
    if (!ready || !iranRef.current) return;

    const sig = `${showIran}#${iranStrikes.map(s => `${s.id}:${s.confidence}`).join('|')}`;
    if (sig === iranSigRef.current) return;
    iranSigRef.current = sig;

    iranRef.current.clearLayers();
    if (!showIran) return;

    iranStrikes.forEach(strike => {
      if (!strike.latitude || !strike.longitude) return;
      const conf = CONFIDENCE[strike.confidence] || CONFIDENCE.LOW;
      const evType = IRAN_EVENT_TYPES[strike.event_type] || IRAN_EVENT_TYPES.strike;
      const confLabel = t(`confidence.${strike.confidence}`, { defaultValue: t('confidence.LOW') });
      const typeLabel = t(`iranEventTypes.${strike.event_type}`, { defaultValue: t('iranEventTypes.strike') });
      const sz = strike.confidence === 'HIGH' ? 18 : strike.confidence === 'MEDIUM' ? 14 : 10;

      const icon = L.divIcon({
        className: '',
        iconSize: [sz + 8, sz + 8],
        iconAnchor: [(sz + 8) / 2, (sz + 8) / 2],
        html: `<div style="
          width:${sz}px;height:${sz}px;
          background:${evType.color}30;
          border:2px solid ${evType.color};
          border-radius:50%;
          display:flex;align-items:center;justify-content:center;
          font-size:${sz - 4}px;
          box-shadow:0 0 ${sz}px ${conf.color}80;
          position:relative;
        ">
          ${evType.icon}
          <div style="
            position:absolute;bottom:-4px;inset-inline-end:-4px;
            width:8px;height:8px;
            border-radius:50%;
            background:${conf.color};
            border:1px solid #000;
          "></div>
        </div>`,
      });

      const videoLink = safeUrl(strike.video_url);
      const sourceLink = safeUrl(strike.url);
      const m = L.marker([strike.latitude, strike.longitude], { icon }).bindPopup(popupShell(`
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">
            <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${conf.color}20;color:${conf.color};border:1px solid ${conf.color}40">
              ${conf.icon} ${esc(confLabel)}
            </span>
            <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${evType.color}20;color:${evType.color}">
              ${evType.icon} ${esc(typeLabel)}
            </span>
            ${videoLink ? `<a href="${esc(videoLink)}" target="_blank" rel="noopener noreferrer" style="font-size:11px;padding:2px 6px;border-radius:4px;background:#7c3aed20;color:#c4b5fd">${esc(t('map.osintVideo'))}</a>` : ''}
          </div>
          <h3 style="font-size:13px;font-weight:700;margin-bottom:4px;line-height:1.5">${esc(strike.title)}</h3>
          <p style="font-size:11px;color:#cbd5e1;margin-bottom:6px">${esc((strike.description || '').substring(0, 120))}</p>
          <div style="font-size:11px;color:#94a3b8;display:flex;justify-content:space-between;gap:8px">
            <span>📍 ${esc(strike.location_name || strike.country || '')}</span>
            <span>${esc(strike.feed_name || '')}</span>
          </div>
          ${sourceLink ? `<a href="${esc(sourceLink)}" target="_blank" rel="noopener noreferrer" style="display:block;margin-top:6px;font-size:11px;color:#67e8f9">${esc(t('map.sourceLink'))}</a>` : ''}
        `, 240), { maxWidth: 300 });

      m.on('click', () => onSelectEvent?.(strike));
      iranRef.current.addLayer(m);
    });
  }, [iranStrikes, showIran, ready, onSelectEvent, t, popupShell]);

  // ===== طبقة المنشآت النووية ☢️ =====
  useEffect(() => {
    if (!ready || !nuclearRef.current) return;
    nuclearRef.current.clearLayers();
    if (!showNuclear) return;

    nuclearFacilities.forEach(fac => {
      if (typeof fac.latitude !== 'number' || typeof fac.longitude !== 'number') return;
      const typeInfo = NUCLEAR_TYPES[fac.type] || NUCLEAR_TYPES.research;
      const typeLabel = t(`nuclearTypes.${fac.type}`, { defaultValue: fac.type || '-' });
      const statusColor = NUCLEAR_STATUS_COLORS[fac.status] || '#94a3b8';
      const statusLabel = t(`nuclearStatus.${fac.status}`, { defaultValue: fac.status || '-' });
      const isOperational = fac.status === 'operational';
      const sz = fac.type === 'power' ? 22 : 18;
      const name = fac.name_ar || fac.name_en || '';

      const pulse = isOperational
        ? `box-shadow:0 0 ${sz}px ${typeInfo.color}80;animation:nuclear-pulse 2.5s ease-in-out infinite;`
        : `box-shadow:0 0 6px ${typeInfo.color}40;opacity:0.7;`;

      const icon = L.divIcon({
        className: '',
        iconSize: [sz + 6, sz + 6],
        iconAnchor: [(sz + 6) / 2, (sz + 6) / 2],
        // esc() على سمة title أيضاً — كانت الوحيدة غير المهرَّبة في الملف
        html: `<div title="${esc(name)}" style="
          width:${sz}px;height:${sz}px;
          background:${typeInfo.color}20;
          border:2px solid ${typeInfo.color};
          border-radius:50%;
          display:flex;align-items:center;justify-content:center;
          font-size:${sz - 6}px;
          ${pulse}
          cursor:pointer;
        ">☢️</div>`,
      });

      const capacity = fac.capacity_mw
        ? `<div>${esc(t('map.capacity'))}: <span style="color:#fbbf24">${esc(fac.capacity_mw)} MW</span></div>` : '';
      const firstGrid = fac.first_grid
        ? `<div>${esc(t('map.firstGrid'))}: <span style="color:#cbd5e1">${esc(fac.first_grid)}</span></div>` : '';
      const notes = fac.notes
        ? `<div style="margin-top:6px;padding:6px;background:#1e293b;border-radius:4px;color:#cbd5e1;font-size:11px">${esc(fac.notes)}</div>` : '';

      const m = L.marker([fac.latitude, fac.longitude], { icon }).bindPopup(popupShell(`
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">
            <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${typeInfo.color}20;color:${typeInfo.color};border:1px solid ${typeInfo.color}40">
              ☢️ ${esc(typeLabel)}
            </span>
            <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${statusColor}20;color:${statusColor}">
              ${esc(statusLabel)}
            </span>
          </div>
          <h3 style="font-size:13px;font-weight:700;margin-bottom:6px;line-height:1.5;color:#fbbf24">${esc(name)}</h3>
          <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px">${esc(fac.name_en || '')}</div>
          <div style="font-size:12px;color:#e2e8f0;line-height:1.8">
            <div>${esc(t('map.country'))}: <span style="color:#67e8f9">${esc(fac.country || '-')}</span></div>
            <div>${esc(t('map.type'))}: <span style="color:#cbd5e1">${esc(fac.reactor_type || '-')}</span></div>
            ${capacity}
            ${firstGrid}
            ${fac.operator ? `<div>${esc(t('map.operator'))}: <span style="color:#cbd5e1">${esc(fac.operator)}</span></div>` : ''}
          </div>
          ${notes}
          <div style="font-size:11px;color:#94a3b8;margin-top:6px;font-family:monospace">
            ${fac.latitude.toFixed(3)}, ${fac.longitude.toFixed(3)}
          </div>
        `, 240), { maxWidth: 320 });
      nuclearRef.current.addLayer(m);
    });
  }, [nuclearFacilities, showNuclear, ready, t, popupShell]);

  // ===== طبقة القواعد العسكرية ⚔️ =====
  useEffect(() => {
    if (!ready || !basesRef.current) return;
    basesRef.current.clearLayers();
    if (!showBases) return;
    militaryBases.forEach(b => {
      if (typeof b.latitude !== 'number' || typeof b.longitude !== 'number') return;
      const typeIcon = b.type === 'naval' ? '⚓' : b.type === 'air' ? '✈️' : b.type === 'ground' ? '🪖' : '⚔️';
      const icon = L.divIcon({
        className: '',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
        html: `<div title="${esc(b.name_ar || b.name_en || '')}" style="width:18px;height:18px;background:rgba(167,139,250,0.15);border:1.5px solid #a78bfa;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:11px;box-shadow:0 0 6px rgba(167,139,250,0.4)">${typeIcon}</div>`,
      });
      const m = L.marker([b.latitude, b.longitude], { icon }).bindPopup(popupShell(`
          <div style="font-size:13px;font-weight:700;color:#c4b5fd;margin-bottom:4px">${esc(b.name_ar || b.name_en || '')}</div>
          <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px">${esc(b.name_en || '')}</div>
          <div style="font-size:12px;color:#e2e8f0;line-height:1.7">
            <div>${esc(t('map.country'))}: <span style="color:#67e8f9">${esc(b.country || '-')}</span></div>
            <div>${esc(t('map.operator'))}: <span style="color:#fbbf24">${esc(b.operator || '-')}</span></div>
            <div>${esc(t('map.type'))}: <span style="color:#cbd5e1">${esc(b.type || '-')}</span></div>
          </div>
          ${b.notes ? `<div style="margin-top:6px;padding:6px;background:#1e293b;border-radius:4px;color:#cbd5e1;font-size:11px">${esc(b.notes)}</div>` : ''}
        `), { maxWidth: 280 });
      basesRef.current.addLayer(m);
    });
  }, [militaryBases, showBases, ready, t, popupShell]);

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
      const capacity = p.capacity_mbpd
        ? `${esc(p.capacity_mbpd)} ${esc(t('map.mbpd'))}`
        : p.capacity_bcm ? `${esc(p.capacity_bcm)} ${esc(t('map.bcm'))}` : '-';
      line.bindPopup(popupShell(`
          <div style="font-size:13px;font-weight:700;color:${color};margin-bottom:4px">${p.type === 'oil' ? '🛢️' : '🔥'} ${esc(p.name_ar || p.name_en || '')}</div>
          <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px">${esc(p.name_en || '')}</div>
          <div style="font-size:12px;color:#e2e8f0;line-height:1.7">
            <div>${esc(t('map.length'))}: <span style="color:#67e8f9">${esc(p.length_km || '-')} ${esc(t('map.kmShort'))}</span></div>
            <div>${esc(t('map.capacity'))}: <span style="color:#fbbf24">${capacity}</span></div>
            <div>${esc(t('map.operator'))}: <span style="color:#cbd5e1">${esc(p.operator || '-')}</span></div>
            <div>${esc(t('map.status'))}: <span style="color:#cbd5e1">${esc(p.status || '-')}</span></div>
          </div>
        `));
      pipelinesRef.current.addLayer(line);
    });
  }, [pipelines, showPipelines, ready, t, popupShell]);

  useEffect(() => {
    if (selectedEvent?.latitude && mapInstance.current) {
      mapInstance.current.flyTo([selectedEvent.latitude, selectedEvent.longitude], 8, { duration: 1 });
    }
  }, [selectedEvent]);

  const layerToggles = [
    ['events', t('map.events'), 'accent-cyan-400'],
    ['flights', t('map.flights'), 'accent-purple-400'],
    ['iran', '🇮🇷 ' + t('map.iran'), 'accent-red-400'],
    ['nuclear', '☢️ ' + t('map.nuclear'), 'accent-yellow-400'],
    ['bases', '⚔️ ' + t('map.bases'), 'accent-violet-400'],
    ['pipelines', '🛢️ ' + t('map.pipelines'), 'accent-amber-400'],
  ];

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

      <fieldset className="absolute bottom-3 start-3 z-[1000] bg-rasad-panel/95 border border-rasad-border rounded-lg p-3 text-sm max-w-[45vw]">
        <legend className="sr-only">{t('map.layers')}</legend>
        <div className="flex items-center gap-2 mb-2">
          <Layers className="w-4 h-4 text-slate-300" aria-hidden="true" />
          <span className="text-slate-200 font-medium">{t('map.layers')}</span>
        </div>
        {layerToggles.map(([key, label, accent]) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer mb-1">
            {/* أسماء أصناف Tailwind كاملة صراحةً كي لا يحذفها فحص المحتوى الثابت */}
            <input
              type="checkbox"
              checked={Boolean(layers[key])}
              onChange={e => onLayerChange?.(key, e.target.checked)}
              className={`w-4 h-4 ${accent} focus-ring`}
            />
            <span className="text-slate-200">{label}</span>
          </label>
        ))}
      </fieldset>

      <div className="absolute bottom-3 end-3 z-[1000] bg-rasad-panel/95 border border-rasad-border rounded-lg p-3 hidden sm:block">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {Object.entries(CATEGORIES).map(([k, c]) => (
            <div key={k} className="flex items-center gap-1">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: c.color }} aria-hidden="true" />
              <span className="text-xs text-slate-200">{c.icon} {t(`categories.${k}`)}</span>
            </div>
          ))}
        </div>
      </div>

      {flights && (
        <div className="absolute top-3 end-3 z-[1000] bg-rasad-panel/95 border border-rasad-border rounded-lg px-2.5 py-1.5 text-xs flex gap-3">
          <span className="text-slate-200">✈️ <span className="font-mono text-white">{flights.total || 0}</span></span>
          <span className="text-purple-300">⚔️ <span className="font-mono text-purple-200">{flights.military || 0}</span></span>
        </div>
      )}
    </div>
  );
}
