/**
 * رصد - الخريطة التفاعلية
 */
import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORIES, SEVERITIES, timeAgo, COUNTRIES, CONFIDENCE, IRAN_EVENT_TYPES } from '../../utils/constants';
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

export default function RasadMap({ events = [], flights = null, iranStrikes = [], selectedEvent, onSelectEvent }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef(null);
  const flightsRef = useRef(null);
  const iranRef = useRef(null);
  const [showFlights, setShowFlights] = useState(true);
  const [showEvents, setShowEvents] = useState(true);
  const [showIran, setShowIran] = useState(true);
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
            <h3 style="font-size:12px;font-weight:700;margin-bottom:4px;line-height:1.5">${ev.title}</h3>
            <p style="font-size:10px;color:#94a3b8;margin-bottom:6px">${(ev.description||'').substring(0,100)}</p>
            <div style="display:flex;justify-content:space-between;font-size:9px;color:#64748b">
              <span>${flag} ${ev.country||''}</span><span>${timeAgo(ev.event_date)}</span>
            </div>
            ${ev.url ? `<a href="${ev.url}" target="_blank" style="display:block;margin-top:6px;font-size:10px;color:#22d3ee">المصدر ←</a>` : ''}
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
          return `<div class="rasad-cluster-item" data-id="${ev.id}" style="padding:4px 0;border-bottom:1px solid #1e293b;font-size:10px;line-height:1.5;cursor:pointer;color:#cbd5e1" onmouseover="this.style.color='#22d3ee'" onmouseout="this.style.color='#cbd5e1'">${cat.icon} ${ev.title.substring(0, 60)}</div>`;
        }).join('');
        const moreText = count > 8 ? `<div style="font-size:9px;color:#64748b;padding-top:4px">+ ${count - 8} أحداث أخرى</div>` : '';

        const m = L.marker([cluster.lat, cluster.lng], { icon }).bindPopup(`
          <div style="min-width:240px;max-height:250px;overflow-y:auto;font-family:Tajawal,sans-serif;direction:rtl">
            <div style="font-size:11px;font-weight:700;margin-bottom:6px;color:#22d3ee">${count} أحداث في هذه المنطقة</div>
            ${listHtml}
            ${moreText}
          </div>`, { maxWidth: 300 });

        // عند الضغط — تكبير إذا الزوم منخفض
        m.on('popupopen', () => {
          setTimeout(() => {
            document.querySelectorAll('.rasad-cluster-item').forEach(el => {
              el.addEventListener('click', () => {
                const id = parseInt(el.dataset.id);
                const ev = events.find(e => e.id === id);
                if (ev) {
                  onSelectEvent?.(ev);
                  if (ev.url) window.open(ev.url, '_blank');
                }
              });
            });
          }, 100);
        });

        m.on('click', () => {
          if (mapInstance.current && zoomLevel < 8) {
            mapInstance.current.flyTo([cluster.lat, cluster.lng], zoomLevel + 2, { duration: 0.5 });
          }
        });

        markersRef.current.addLayer(m);
      }
    });

    // دالة اختيار حدث من popup التجميع
    window._rasadSelect = (id) => {
      const ev = events.find(e => e.id === id);
      if (ev) onSelectEvent?.(ev);
    };

    return () => { delete window._rasadSelect; };
  }, [events, showEvents, ready, zoomLevel]);

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
          <div style="font-weight:700;font-family:monospace">${f.callsign||f.icao24}</div>
          ${isMil?'<span style="font-size:10px;color:#a855f7">⚔️ عسكري</span>':''}
          <div style="font-size:10px;color:#94a3b8;margin-top:4px">
            ${f.origin_country}<br/>
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
            ${strike.video_url ? `<a href="${strike.video_url}" target="_blank" style="font-size:10px;padding:2px 6px;border-radius:4px;background:#7c3aed20;color:#a78bfa">🎥 فيديو OSINT</a>` : ''}
          </div>
          <h3 style="font-size:12px;font-weight:700;margin-bottom:4px;line-height:1.5">${strike.title}</h3>
          <p style="font-size:10px;color:#94a3b8;margin-bottom:6px">${(strike.description || '').substring(0, 120)}</p>
          <div style="font-size:9px;color:#64748b;display:flex;justify-content:space-between">
            <span>📍 ${strike.location_name || strike.country}</span>
            <span>${strike.feed_name || ''}</span>
          </div>
          ${strike.url ? `<a href="${strike.url}" target="_blank" style="display:block;margin-top:6px;font-size:10px;color:#22d3ee">المصدر ←</a>` : ''}
        </div>`, { maxWidth: 300 });

      m.on('click', () => onSelectEvent?.(strike));
      iranRef.current.addLayer(m);
    });
  }, [iranStrikes, showIran, ready]);

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
        <div className="flex items-center gap-2 mb-2"><Layers className="w-4 h-4 text-slate-400" /><span className="text-slate-400 font-medium">طبقات</span></div>
        {[['الأحداث', showEvents, setShowEvents, 'cyan'], ['الطيران', showFlights, setShowFlights, 'purple'], ['🇮🇷 إيران OSINT', showIran, setShowIran, 'red']].map(([l, v, fn, c]) => (
          <label key={l} className="flex items-center gap-2 cursor-pointer mb-1">
            <input type="checkbox" checked={v} onChange={e => fn(e.target.checked)} className={`w-4 h-4 accent-${c}-400`} />
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
