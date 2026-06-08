/**
 * رصد - الكرة الأرضية ثلاثية الأبعاد (v1.3)
 *
 * تعرض نفس البيانات (أحداث / إيران / مفاعلات / قواعد / أنابيب) على كرة Three.js
 * عبر globe.gl. ليست بديلًا كاملاً عن خريطة Leaflet — وضع تكميلي.
 */
import React, { useEffect, useRef } from 'react';
import Globe from 'globe.gl';
import { useTranslation } from 'react-i18next';
import { CATEGORIES, SEVERITIES, CONFIDENCE } from '../../utils/constants';

const ME_LAT = 29.0;
const ME_LNG = 42.0;

// حجم النقطة (بكسل) حسب الخطورة
function dotSize(severity) {
  return severity === 'critical' ? 16 : severity === 'high' ? 12 : severity === 'medium' ? 9 : 7;
}

// تحويل لون hex إلى rgba بشفافية (لتلاشي حلقات الرادار للخارج)
function hexToRgba(hex, a) {
  if (typeof hex !== 'string') return `rgba(56,189,248,${a})`;
  let h = hex.replace('#', '').trim();
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  const n = parseInt(h, 16);
  if (h.length !== 6 || Number.isNaN(n)) return `rgba(56,189,248,${a})`;
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function eventColor(ev) {
  const cat = CATEGORIES[ev.category] || CATEGORIES.general;
  return cat.color;
}

// عنصر DOM لعلامة نقطية متوهّجة (بديل الأعمدة الأسطوانية) + تلميح يظهر عند المرور.
// globe.gl يموضِع العنصر تلقائياً (translate -50%,-50%) ويُخفيه خلف الكرة.
function makeMarkerEl(d, onSelectEvent) {
  const el = document.createElement('div');
  el.style.cssText = `position:relative;width:${d.size}px;height:${d.size}px;pointer-events:auto;cursor:${d.clickable ? 'pointer' : 'default'};will-change:transform`;

  const dot = document.createElement('div');
  const glow = Math.max(6, Math.round(d.size * 1.1));
  dot.style.cssText = `position:absolute;inset:0;border-radius:50%;background:${d.color};border:1.5px solid rgba(255,255,255,0.9);box-shadow:0 0 ${glow}px ${d.color},0 0 3px rgba(0,0,0,0.7)`;
  el.appendChild(dot);

  if (d.label) {
    const tip = document.createElement('div');
    tip.innerHTML = d.label;
    tip.style.cssText = 'display:none;position:absolute;bottom:150%;left:50%;transform:translateX(-50%);z-index:20;pointer-events:none';
    el.appendChild(tip);
    el.addEventListener('mouseenter', () => { tip.style.display = 'block'; });
    el.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
  }
  if (d.clickable) el.addEventListener('click', () => onSelectEvent?.(d.data));
  return el;
}

export default function RasadGlobe({
  events = [],
  iranStrikes = [],
  nuclearFacilities = [],
  bases = [],
  pipelines = [],
  onSelectEvent,
  showEvents = true,
  showIran = true,
  showNuclear = true,
  showBases = true,
  showPipelines = true,
  selectedEvent,
}) {
  const { t } = useTranslation();
  const containerRef = useRef(null);
  const globeRef = useRef(null);

  // إنشاء الكرة مرة واحدة
  useEffect(() => {
    if (!containerRef.current || globeRef.current) return;
    const w = containerRef.current.clientWidth || 800;
    const h = containerRef.current.clientHeight || 600;

    const g = Globe()(containerRef.current)
      .width(w)
      .height(h)
      .backgroundColor('#0a0e17')
      .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
      .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
      .atmosphereColor('#22d3ee')
      .atmosphereAltitude(0.18)
      .showGraticules(true);

    g.pointOfView({ lat: ME_LAT, lng: ME_LNG, altitude: 1.7 }, 1500);

    // تعطيل auto-rotate تجنبًا للإرباك
    g.controls().autoRotate = false;
    g.controls().enableDamping = true;
    g.controls().dampingFactor = 0.1;

    globeRef.current = g;

    // إعادة الحجم
    const ro = new ResizeObserver(() => {
      if (!containerRef.current || !globeRef.current) return;
      globeRef.current.width(containerRef.current.clientWidth);
      globeRef.current.height(containerRef.current.clientHeight);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      try { globeRef.current?._destructor?.(); } catch {}
      if (containerRef.current) containerRef.current.innerHTML = '';
      globeRef.current = null;
    };
  }, []);

  // العلامات: نقاط متوهّجة عبر طبقة HTML (بديل الأعمدة الأسطوانية)،
  // + حلقات رادار متحرّكة (ringsData) للأحداث الحرجة/المرتفعة والضربات.
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;

    const markers = [];
    const rings = [];

    if (showEvents) {
      events.forEach(ev => {
        if (typeof ev.latitude !== 'number' || typeof ev.longitude !== 'number') return;
        const color = eventColor(ev);
        markers.push({
          lat: ev.latitude, lng: ev.longitude, size: dotSize(ev.severity), color,
          clickable: true, kind: 'event', data: ev,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#111827;border:1px solid #1e293b;padding:6px 8px;border-radius:6px;max-width:280px;white-space:normal">
            <div style="color:${color};font-size:11px;font-weight:700;margin-bottom:2px">${(CATEGORIES[ev.category]||CATEGORIES.general).icon} ${ev.title || ''}</div>
            <div style="color:#94a3b8;font-size:10px">${ev.country || ''}</div>
          </div>`,
        });
        if (ev.severity === 'critical' || ev.severity === 'high') {
          rings.push({ lat: ev.latitude, lng: ev.longitude, color, maxR: ev.severity === 'critical' ? 5 : 3.4, speed: 2.2, period: ev.severity === 'critical' ? 900 : 1300 });
        }
      });
    }
    if (showIran) {
      iranStrikes.forEach(s => {
        if (typeof s.latitude !== 'number' || typeof s.longitude !== 'number') return;
        const conf = CONFIDENCE[s.confidence] || CONFIDENCE.LOW;
        markers.push({
          lat: s.latitude, lng: s.longitude, size: 12, color: conf.color,
          clickable: true, kind: 'iran', data: s,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#111827;border:1px solid ${conf.color};padding:6px 8px;border-radius:6px;max-width:280px;white-space:normal">
            <div style="color:${conf.color};font-size:10px;margin-bottom:2px">${conf.icon} ${conf.label}</div>
            <div style="color:#fff;font-size:11px;font-weight:700">${s.title || ''}</div>
          </div>`,
        });
        if (s.event_type === 'strike') {
          rings.push({ lat: s.latitude, lng: s.longitude, color: conf.color, maxR: 4.5, speed: 2.4, period: 1000 });
        }
      });
    }
    if (showNuclear) {
      nuclearFacilities.forEach(f => {
        if (typeof f.latitude !== 'number' || typeof f.longitude !== 'number') return;
        markers.push({
          lat: f.latitude, lng: f.longitude, size: f.type === 'power' ? 12 : 9, color: '#facc15',
          clickable: false, kind: 'nuclear', data: f,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#0d1117;border:1px solid #facc15;padding:6px 8px;border-radius:6px;max-width:260px;white-space:normal">
            <div style="color:#facc15;font-size:11px;font-weight:700">☢️ ${f.name_ar || f.name_en}</div>
            <div style="color:#94a3b8;font-size:9px">${f.country || ''} • ${f.capacity_mw ? f.capacity_mw + ' MW' : f.type}</div>
          </div>`,
        });
      });
    }
    if (showBases) {
      bases.forEach(b => {
        if (typeof b.latitude !== 'number' || typeof b.longitude !== 'number') return;
        markers.push({
          lat: b.latitude, lng: b.longitude, size: 8, color: '#a78bfa',
          clickable: false, kind: 'base', data: b,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#0d1117;border:1px solid #a78bfa;padding:6px 8px;border-radius:6px;max-width:260px;white-space:normal">
            <div style="color:#a78bfa;font-size:11px;font-weight:700">⚔️ ${b.name_ar || b.name_en}</div>
            <div style="color:#94a3b8;font-size:9px">${b.country || ''} • ${b.operator || ''}</div>
          </div>`,
        });
      });
    }

    g
      .htmlElementsData(markers)
      .htmlLat('lat')
      .htmlLng('lng')
      .htmlAltitude(0.012)
      .htmlElement(d => makeMarkerEl(d, onSelectEvent));

    g
      .ringsData(rings)
      .ringLat('lat')
      .ringLng('lng')
      .ringColor(d => (tt) => hexToRgba(d.color, 1 - tt))
      .ringMaxRadius('maxR')
      .ringPropagationSpeed('speed')
      .ringRepeatPeriod('period');
  }, [events, iranStrikes, nuclearFacilities, bases, showEvents, showIran, showNuclear, showBases, onSelectEvent]);

  // خطوط الأنابيب
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;

    const paths = showPipelines
      ? pipelines.flatMap(p => {
          const coords = (p.coordinates || []).map(([lat, lng]) => ({ lat, lng, alt: 0.01 }));
          return coords.length > 1 ? [{ coords, color: p.type === 'oil' ? '#fbbf24' : '#3b82f6', name: p.name_ar || p.name_en }] : [];
        })
      : [];

    g
      .pathsData(paths)
      .pathPoints('coords')
      .pathPointLat('lat')
      .pathPointLng('lng')
      .pathPointAlt('alt')
      .pathColor(p => p.color)
      .pathStroke(2)
      .pathLabel('name');
  }, [pipelines, showPipelines]);

  // arcs لإحداثيات الضربات الإيرانية (مصدر = طهران)
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    const arcs = (showIran ? iranStrikes : [])
      .filter(s => typeof s.latitude === 'number' && typeof s.longitude === 'number' && s.event_type === 'strike')
      .map(s => {
        const conf = CONFIDENCE[s.confidence] || CONFIDENCE.LOW;
        return { startLat: 35.6892, startLng: 51.389, endLat: s.latitude, endLng: s.longitude, color: conf.color };
      });
    g
      .arcsData(arcs)
      .arcStartLat('startLat').arcStartLng('startLng')
      .arcEndLat('endLat').arcEndLng('endLng')
      .arcColor('color')
      .arcDashLength(0.4)
      .arcDashGap(0.2)
      .arcDashAnimateTime(2000)
      .arcStroke(0.4);
  }, [iranStrikes, showIran]);

  // التركيز على الحدث المختار
  useEffect(() => {
    const g = globeRef.current;
    if (!g || !selectedEvent?.latitude || !selectedEvent?.longitude) return;
    g.pointOfView({ lat: selectedEvent.latitude, lng: selectedEvent.longitude, altitude: 0.9 }, 1200);
  }, [selectedEvent]);

  return <div ref={containerRef} className="w-full h-full" />;
}
