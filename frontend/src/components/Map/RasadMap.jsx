/**
 * رصد - الخريطة التفاعلية
 */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORIES, SEVERITIES, timeAgo, COUNTRIES, CONFIDENCE, IRAN_EVENT_TYPES } from '../../utils/constants';
import { esc, safeUrl } from '../../utils/security';
import { Layers, ZoomIn, ZoomOut, Crosshair } from 'lucide-react';

const ME_CENTER = [29.0, 42.0];
const ME_ZOOM = 5;

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

// ===== ألوان أنواع المنشآت النووية =====
const NUCLEAR_TYPES = {
  power:       { color: '#facc15', label: 'محطة قوة',   icon: '☢️' },
  research:    { color: '#22d3ee', label: 'أبحاث',      icon: '⚛️' },
  enrichment:  { color: '#f97316', label: 'تخصيب',      icon: '☢️' },
  conversion:  { color: '#a78bfa', label: 'تحويل',      icon: '⚗️' },
  heavy_water: { color: '#38bdf8', label: 'ماء ثقيل',   icon: '💧' },
  fuel:        { color: '#fb7185', label: 'وقود',       icon: '⚛️' },
};

const NUCLEAR_STATUS_LABELS = {
  operational:  { ar: 'عاملة',        color: '#22c55e' },
  construction: { ar: 'قيد الإنشاء',  color: '#f59e0b' },
  planned:      { ar: 'مخططة',        color: '#64748b' },
  shutdown:     { ar: 'متوقفة',       color: '#ef4444' },
  modified:     { ar: 'معدّلة',       color: '#a78bfa' },
};

export default function RasadMap({ events = [], flights = null, iranStrikes = [], nuclearFacilities = [], militaryBases = [], pipelines = [], selectedEvent, onSelectEvent }) {
  const { t } = useTranslation();
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef(null);
  const flightsRef = useRef(null);
  const iranRef = useRef(null);
  const nuclearRef = useRef(null);
  const basesRef = useRef(null);
  const pipelinesRef = useRef(null);
  const [showFlights, setShowFlights] = useState(true);
  const [showEvents, setShowEvents] = useState(true);
  const [showIran, setShowIran] = useState(true);
  const [showNuclear, setShowNuclear] = useState(true);
  const [showBases, setShowBases] = useState(false);
  const [showPipelines, setShowPipelines] = useState(false);
  const [ready, setReady] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(ME_ZOOM);

  useEffect(() => {
    if (mapInstance.current || !mapRef.current) return;
    const map = L.map(mapRef.current, {
      center: ME_CENTER, zoom: ME_ZOOM, zoomControl: false, attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
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
    return () => { map.remove(); mapInstance.current = null; };
  }, []);

  useEffect(() => {
    if (!ready || !markersRef.current) return;
    markersRef.current.clearLayers();
    if (!showEvents) return;

    const clusters = clusterEvents(events, zoomLevel);

    clusters.forEach(cluster => {
      if (cluster.events.length === 1) {
        // نقطة واحدة — ارسمها عادي
        const ev = cluster.events[0];
        const cat = CATEGORIES[ev.category] || CATEGORIES.general;
        const sev = SEVERITIES[ev.severity] || SEVERITIES.low;
        const sz = ev.severity === 'critical' ? 16 : ev.severity === 'high' ? 12 : 9;
        const icon = L.divIcon({
          className: '', iconSize: [sz, sz], iconAnchor: [sz/2, sz/2],
          html: `<div class="event-marker ${ev.severity === 'critical' ? 'critical' : ''}" style="width:${sz}px;height:${sz}px;background:${cat.color};border-color:${cat.color};box-shadow:0 0 ${sz}px ${cat.color}40;"></div>`,
        });
        const flag = COUNTRIES[ev.country_code]?.flag || '🌍';
        const m = L.marker([ev.latitude, ev.longitude], { icon }).bindPopup(`
          <div style="min-width:220px;font-family:Tajawal,sans-serif;direction:rtl">
            <div style="display:flex;gap:4px;margin-bottom:6px">
              <span style="font-size:16px">${cat.icon}</span>
              <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:${cat.color}20;color:${cat.color}">${cat.label}</span>
              <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:${sev.color}20;color:${sev.color}">${sev.label}</span>
            </div>
            <h3 style="font-size:12px;font-weight:700;margin-bottom:4px;line-height:1.5">${esc(ev.title)}</h3>
            <p style="font-size:10px;color:#94a3b8;margin-bottom:6px">${esc((ev.description||'').substring(0,100))}</p>
            <div style="display:flex;justify-content:space-between;font-size:9px;color:#64748b">
              <span>${flag} ${esc(ev.country||'')}</span><span>${timeAgo(ev.event_date)}</span>
            </div>
            ${safeUrl(ev.url) ? `<a href="${esc(safeUrl(ev.url))}" target="_blank" rel="noopener noreferrer" style="display:block;margin-top:6px;font-size:10px;color:#22d3ee">المصدر ←</a>` : ''}
          </div>`, { maxWidth: 280 });
        m.on('click', () => onSelectEvent?.(ev));
        markersRef.current.addLayer(m);
      } else {
        // مجموعة نقاط — ارسم دائرة تجميع
        const count = cluster.events.length;
        const hasCritical = cluster.events.some(e => e.severity === 'critical' || e.severity === 'high');
        const color = hasCritical ? '#ef4444' : '#22d3ee';
        const sz = Math.min(20 + count * 2, 44);
        const icon = L.divIcon({
          className: '', iconSize: [sz, sz], iconAnchor: [sz/2, sz/2],
          html: `<div style="width:${sz}px;height:${sz}px;background:${color}30;border:2px solid ${color};border-radius:50%;display:flex;align-items:center;justify-content:center;color:${color};font-weight:700;font-size:${sz > 30 ? 13 : 11}px;font-family:monospace;box-shadow:0 0 12px ${color}50;cursor:pointer">${count}</div>`,
        });

        // قائمة العناوين في popup التجميع
        const listHtml = cluster.events.slice(0, 8).map(ev => {
          const cat = CATEGORIES[ev.category] || CATEGORIES.general;
          return `<div class="rasad-cluster-item" data-id="${ev.id}" style="padding:4px 0;border-bottom:1px solid #1e293b;font-size:10px;line-height:1.5;cursor:pointer;color:#cbd5e1" onmouseover="this.style.color='#22d3ee'" onmouseout="this.style.color='#cbd5e1'">${cat.icon} ${esc((ev.title || '').substring(0, 60))}</div>`;
        }).join('');
        const moreText = count > 8 ? `<div style="font-size:9px;color:#64748b;padding-top:4px">+ ${count - 8} أحداث أخرى</div>` : '';

        const m = L.marker([cluster.lat, cluster.lng], { icon }).bindPopup(`
          <div style="min-width:240px;max-height:250px;overflow-y:auto;font-family:Tajawal,sans-serif;direction:rtl">
            <div style="font-size:11px;font-weight:700;margin-bottom:6px;color:#22d3ee">${count} أحداث في هذه المنطقة</div>
            ${listHtml}
            ${moreText}
          </div>`, { maxWidth: 300 });

        // تفويض حدث واحد على عنصر الـ popup نفسه (بدل مستمعات عامة على المستند
        // تتراكم عند كل فتح) — يُنظَّف تلقائياً مع إزالة الـ popup.
        m.on('popupopen', (e) => {
          const root = e.popup.getElement();
          if (!root) return;
          root.addEventListener('click', (ev2) => {
            const item = ev2.target.closest('.rasad-cluster-item');
            if (!item) return;
            const id = parseInt(item.dataset.id, 10);
            const found = events.find(x => x.id === id);
            if (found) {
              onSelectEvent?.(found);
              const u = safeUrl(found.url);
              if (u) window.open(u, '_blank', 'noopener');
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

  }, [events, showEvents, ready, zoomLevel, onSelectEvent]);

  useEffect(() => {
    if (!ready || !flightsRef.current) return;
    flightsRef.current.clearLayers();
    if (!showFlights || !flights?.flights) return;
    flights.flights.forEach(f => {
      if (!f.latitude || !f.longitude) return;
      const isMil = f.is_military;
      const sz = isMil ? 18 : 10;
      const icon = L.divIcon({
        className: '', iconSize: [sz, sz], iconAnchor: [sz/2, sz/2],
        html: `<div style="transform:rotate(${f.heading||0}deg);font-size:${sz}px;filter:drop-shadow(0 0 3px ${isMil?'#a855f7':'#475569'})">✈️</div>`,
      });
      L.marker([f.latitude, f.longitude], { icon }).bindPopup(`
        <div style="min-width:160px;font-family:Tajawal,sans-serif;direction:rtl">
          <div style="font-weight:700;font-family:monospace">${esc(f.callsign||f.icao24)}</div>
          ${isMil?'<span style="font-size:10px;color:#a855f7">⚔️ عسكري</span>':''}
          <div style="font-size:10px;color:#94a3b8;margin-top:4px">
            ${esc(f.origin_country||'')}<br/>
            الارتفاع: ${f.altitude?Math.round(f.altitude)+'م':'—'}<br/>
            السرعة: ${f.velocity?Math.round(f.velocity*3.6)+' كم/س':'—'}
          </div>
        </div>`).addTo(flightsRef.current);
    });
  }, [flights, showFlights, ready]);

  // طبقة أحداث إيران OSINT
  useEffect(() => {
    if (!ready || !iranRef.current) return;
    iranRef.current.clearLayers();
    if (!showIran) return;

    iranStrikes.forEach(strike => {
      if (!strike.latitude || !strike.longitude) return;
      const conf = CONFIDENCE[strike.confidence] || CONFIDENCE.LOW;
      const evType = IRAN_EVENT_TYPES[strike.event_type] || IRAN_EVENT_TYPES.strike;
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
            position:absolute;bottom:-4px;right:-4px;
            width:8px;height:8px;
            border-radius:50%;
            background:${conf.color};
            border:1px solid #000;
          "></div>
        </div>`,
      });

      const m = L.marker([strike.latitude, strike.longitude], { icon }).bindPopup(`
        <div style="min-width:240px;font-family:Tajawal,sans-serif;direction:rtl">
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">
            <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:${conf.color}20;color:${conf.color};border:1px solid ${conf.color}40">
              ${conf.icon} ${conf.label}
            </span>
            <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:${evType.color}20;color:${evType.color}">
              ${evType.icon} ${evType.label}
            </span>
            ${safeUrl(strike.video_url) ? `<a href="${esc(safeUrl(strike.video_url))}" target="_blank" rel="noopener noreferrer" style="font-size:10px;padding:2px 6px;border-radius:4px;background:#7c3aed20;color:#a78bfa">🎥 فيديو OSINT</a>` : ''}
          </div>
          <h3 style="font-size:12px;font-weight:700;margin-bottom:4px;line-height:1.5">${esc(strike.title)}</h3>
          <p style="font-size:10px;color:#94a3b8;margin-bottom:6px">${esc((strike.description || '').substring(0, 120))}</p>
          <div style="font-size:9px;color:#64748b;display:flex;justify-content:space-between">
            <span>📍 ${esc(strike.location_name || strike.country || '')}</span>
            <span>${esc(strike.feed_name || '')}</span>
          </div>
          ${safeUrl(strike.url) ? `<a href="${esc(safeUrl(strike.url))}" target="_blank" rel="noopener noreferrer" style="display:block;margin-top:6px;font-size:10px;color:#22d3ee">المصدر ←</a>` : ''}
        </div>`, { maxWidth: 300 });

      m.on('click', () => onSelectEvent?.(strike));
      iranRef.current.addLayer(m);
    });
  }, [iranStrikes, showIran, ready, onSelectEvent]);

  // طبقة المنشآت النووية ☢️
  useEffect(() => {
    if (!ready || !nuclearRef.current) return;
    nuclearRef.current.clearLayers();
    if (!showNuclear) return;

    nuclearFacilities.forEach(fac => {
      if (typeof fac.latitude !== 'number' || typeof fac.longitude !== 'number') return;
      const typeInfo = NUCLEAR_TYPES[fac.type] || NUCLEAR_TYPES.research;
      const statusInfo = NUCLEAR_STATUS_LABELS[fac.status] || { ar: fac.status || '-', color: '#64748b' };
      const isOperational = fac.status === 'operational';
      const sz = fac.type === 'power' ? 22 : 18;

      const pulse = isOperational ? `box-shadow:0 0 ${sz}px ${typeInfo.color}80;animation:nuclear-pulse 2.5s ease-in-out infinite;` : `box-shadow:0 0 6px ${typeInfo.color}40;opacity:0.7;`;

      const icon = L.divIcon({
        className: '',
        iconSize: [sz + 6, sz + 6],
        iconAnchor: [(sz + 6) / 2, (sz + 6) / 2],
        html: `<div title="${fac.name_ar || fac.name_en}" style="
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

      const capacity = fac.capacity_mw ? `<div>السعة: <span style="color:#fbbf24">${esc(fac.capacity_mw)} MW</span></div>` : '';
      const firstGrid = fac.first_grid ? `<div>بدء التشغيل: <span style="color:#94a3b8">${esc(fac.first_grid)}</span></div>` : '';
      const notes = fac.notes ? `<div style="margin-top:6px;padding:6px;background:#1e293b;border-radius:4px;color:#cbd5e1;font-size:9px">${esc(fac.notes)}</div>` : '';

      const m = L.marker([fac.latitude, fac.longitude], { icon }).bindPopup(`
        <div style="min-width:240px;font-family:Tajawal,sans-serif;direction:rtl">
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">
            <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:${typeInfo.color}20;color:${typeInfo.color};border:1px solid ${typeInfo.color}40">
              ☢️ ${typeInfo.label}
            </span>
            <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:${statusInfo.color}20;color:${statusInfo.color}">
              ${esc(statusInfo.ar)}
            </span>
          </div>
          <h3 style="font-size:13px;font-weight:700;margin-bottom:6px;line-height:1.5;color:#fbbf24">${esc(fac.name_ar || fac.name_en)}</h3>
          <div style="font-size:10px;color:#94a3b8;margin-bottom:6px">${esc(fac.name_en || '')}</div>
          <div style="font-size:11px;color:#cbd5e1;line-height:1.8">
            <div>الدولة: <span style="color:#22d3ee">${esc(fac.country || '-')}</span></div>
            <div>النوع: <span style="color:#94a3b8">${esc(fac.reactor_type || '-')}</span></div>
            ${capacity}
            ${firstGrid}
            ${fac.operator ? `<div>المُشغّل: <span style="color:#94a3b8">${esc(fac.operator)}</span></div>` : ''}
          </div>
          ${notes}
          <div style="font-size:9px;color:#64748b;margin-top:6px;font-family:monospace">
            ${fac.latitude.toFixed(3)}, ${fac.longitude.toFixed(3)}
          </div>
        </div>`, { maxWidth: 320 });
      nuclearRef.current.addLayer(m);
    });
  }, [nuclearFacilities, showNuclear, ready]);

  // طبقة القواعد العسكرية ⚔️ (v1.3)
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
        html: `<div style="width:18px;height:18px;background:rgba(167,139,250,0.15);border:1.5px solid #a78bfa;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:11px;box-shadow:0 0 6px rgba(167,139,250,0.4)">${typeIcon}</div>`,
      });
      const m = L.marker([b.latitude, b.longitude], { icon }).bindPopup(`
        <div style="min-width:220px;font-family:Tajawal,sans-serif;direction:rtl">
          <div style="font-size:12px;font-weight:700;color:#a78bfa;margin-bottom:4px">${esc(b.name_ar || b.name_en)}</div>
          <div style="font-size:10px;color:#94a3b8;margin-bottom:6px">${esc(b.name_en || '')}</div>
          <div style="font-size:11px;color:#cbd5e1;line-height:1.7">
            <div>الدولة: <span style="color:#22d3ee">${esc(b.country || '-')}</span></div>
            <div>المُشغّل: <span style="color:#fbbf24">${esc(b.operator || '-')}</span></div>
            <div>النوع: <span style="color:#94a3b8">${esc(b.type || '-')}</span></div>
          </div>
          ${b.notes ? `<div style="margin-top:6px;padding:6px;background:#1e293b;border-radius:4px;color:#cbd5e1;font-size:9px">${esc(b.notes)}</div>` : ''}
        </div>`, { maxWidth: 280 });
      basesRef.current.addLayer(m);
    });
  }, [militaryBases, showBases, ready]);

  // طبقة خطوط الأنابيب 🛢️ (v1.3)
  useEffect(() => {
    if (!ready || !pipelinesRef.current) return;
    pipelinesRef.current.clearLayers();
    if (!showPipelines) return;
    pipelines.forEach(p => {
      if (!Array.isArray(p.coordinates) || p.coordinates.length < 2) return;
      const color = p.type === 'oil' ? '#fbbf24' : '#3b82f6';
      const line = L.polyline(p.coordinates, {
        color, weight: 3, opacity: 0.7, dashArray: p.status === 'partial' ? '5, 8' : null,
      });
      line.bindPopup(`
        <div style="min-width:220px;font-family:Tajawal,sans-serif;direction:rtl">
          <div style="font-size:12px;font-weight:700;color:${color};margin-bottom:4px">${p.type === 'oil' ? '🛢️' : '🔥'} ${esc(p.name_ar || p.name_en)}</div>
          <div style="font-size:10px;color:#94a3b8;margin-bottom:6px">${esc(p.name_en || '')}</div>
          <div style="font-size:11px;color:#cbd5e1;line-height:1.7">
            <div>الطول: <span style="color:#22d3ee">${esc(p.length_km || '-')} كم</span></div>
            <div>السعة: <span style="color:#fbbf24">${p.capacity_mbpd ? esc(p.capacity_mbpd) + ' مليون برميل/يوم' : p.capacity_bcm ? esc(p.capacity_bcm) + ' BCM' : '-'}</span></div>
            <div>المُشغّل: <span style="color:#94a3b8">${esc(p.operator || '-')}</span></div>
            <div>الحالة: <span style="color:#94a3b8">${esc(p.status || '-')}</span></div>
          </div>
        </div>`);
      pipelinesRef.current.addLayer(line);
    });
  }, [pipelines, showPipelines, ready]);

  useEffect(() => {
    if (selectedEvent?.latitude && mapInstance.current) {
      mapInstance.current.flyTo([selectedEvent.latitude, selectedEvent.longitude], 8, { duration: 1 });
    }
  }, [selectedEvent]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />
      <div className="absolute top-3 left-3 z-[1000] flex flex-col gap-2">
        {[
          { fn: () => mapInstance.current?.zoomIn(), icon: <ZoomIn className="w-5 h-5" /> },
          { fn: () => mapInstance.current?.zoomOut(), icon: <ZoomOut className="w-5 h-5" /> },
          { fn: () => mapInstance.current?.flyTo(ME_CENTER, ME_ZOOM, { duration: 0.5 }), icon: <Crosshair className="w-5 h-5" /> },
        ].map((b, i) => (
          <button key={i} onClick={b.fn} className="w-11 h-11 bg-[#111827] border border-[#1e293b] rounded-lg flex items-center justify-center hover:bg-[#1e293b] text-cyan-400">{b.icon}</button>
        ))}
      </div>
      <div className="absolute bottom-3 left-3 z-[1000] bg-[#111827]/95 border border-[#1e293b] rounded-lg p-3 text-sm">
        <div className="flex items-center gap-2 mb-2"><Layers className="w-4 h-4 text-slate-400" /><span className="text-slate-400 font-medium">{t('map.layers')}</span></div>
        {[
          // ملاحظة: أسماء أصناف Tailwind كاملة صراحةً كي لا يحذفها فحص المحتوى الثابت
          [t('map.events'), showEvents, setShowEvents, 'accent-cyan-400'],
          [t('map.flights'), showFlights, setShowFlights, 'accent-purple-400'],
          ['🇮🇷 ' + t('map.iran'), showIran, setShowIran, 'accent-red-400'],
          ['☢️ ' + t('map.nuclear'), showNuclear, setShowNuclear, 'accent-yellow-400'],
          ['⚔️ ' + t('map.bases'), showBases, setShowBases, 'accent-violet-400'],
          ['🛢️ ' + t('map.pipelines'), showPipelines, setShowPipelines, 'accent-amber-400'],
        ].map(([l, v, fn, c]) => (
          <label key={l} className="flex items-center gap-2 cursor-pointer mb-1">
            <input type="checkbox" checked={v} onChange={e => fn(e.target.checked)} className={`w-4 h-4 ${c}`} />
            <span className="text-slate-300">{l}</span>
          </label>
        ))}
      </div>
      <div className="absolute bottom-3 right-3 z-[1000] bg-[#111827]/95 border border-[#1e293b] rounded-lg p-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {Object.entries(CATEGORIES).map(([k, c]) => (
            <div key={k} className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full" style={{background:c.color}}/><span className="text-xs text-slate-400">{c.icon} {c.label}</span></div>
          ))}
        </div>
      </div>
      {flights && (
        <div className="absolute top-3 right-3 z-[1000] bg-[#111827]/95 border border-[#1e293b] rounded-lg px-2.5 py-1.5 text-[10px] flex gap-3">
          <span className="text-slate-400">✈️ <span className="font-mono text-white">{flights.total||0}</span></span>
          <span className="text-purple-400">⚔️ <span className="font-mono text-purple-300">{flights.military||0}</span></span>
        </div>
      )}
    </div>
  );
}
