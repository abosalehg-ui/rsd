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

// نصف قطر النقطة (بدرجات globe.gl) حسب الخطورة
function pointRad(severity) {
  return severity === 'critical' ? 0.5 : severity === 'high' ? 0.4 : severity === 'medium' ? 0.3 : 0.22;
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

  // العلامات: نقاط منخفضة (أقراص ملوّنة) عبر طبقة pointsData — بديل الأعمدة الطويلة،
  // + حلقات رادار متحرّكة (ringsData) للأحداث الحرجة/المرتفعة والضربات.
  // ملاحظة: لا نستخدم طبقة htmlElementsData لأنها تستدعي isBehindGlobe الذي ينهار
  // مع وجود نسختَي three مختلفتين (التطبيق 0.169 / المحزومة في globe.gl 0.184).
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;

    const points = [];
    const rings = [];

    if (showEvents) {
      events.forEach(ev => {
        if (typeof ev.latitude !== 'number' || typeof ev.longitude !== 'number') return;
        const color = eventColor(ev);
        points.push({
          lat: ev.latitude, lng: ev.longitude, radius: pointRad(ev.severity), color,
          kind: 'event', data: ev,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#111827;border:1px solid #1e293b;padding:6px 8px;border-radius:6px;max-width:280px">
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
        points.push({
          lat: s.latitude, lng: s.longitude, radius: 0.42, color: conf.color,
          kind: 'iran', data: s,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#111827;border:1px solid ${conf.color};padding:6px 8px;border-radius:6px;max-width:280px">
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
        points.push({
          lat: f.latitude, lng: f.longitude, radius: f.type === 'power' ? 0.46 : 0.36, color: '#facc15',
          kind: 'nuclear', data: f,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#0d1117;border:1px solid #facc15;padding:6px 8px;border-radius:6px;max-width:260px">
            <div style="color:#facc15;font-size:11px;font-weight:700">☢️ ${f.name_ar || f.name_en}</div>
            <div style="color:#94a3b8;font-size:9px">${f.country || ''} • ${f.capacity_mw ? f.capacity_mw + ' MW' : f.type}</div>
          </div>`,
        });
      });
    }
    if (showBases) {
      bases.forEach(b => {
        if (typeof b.latitude !== 'number' || typeof b.longitude !== 'number') return;
        points.push({
          lat: b.latitude, lng: b.longitude, radius: 0.28, color: '#a78bfa',
          kind: 'base', data: b,
          label: `<div style="direction:rtl;font-family:Tajawal,sans-serif;background:#0d1117;border:1px solid #a78bfa;padding:6px 8px;border-radius:6px;max-width:260px">
            <div style="color:#a78bfa;font-size:11px;font-weight:700">⚔️ ${b.name_ar || b.name_en}</div>
            <div style="color:#94a3b8;font-size:9px">${b.country || ''} • ${b.operator || ''}</div>
          </div>`,
        });
      });
    }

    g
      .pointsData(points)
      .pointLat('lat')
      .pointLng('lng')
      .pointAltitude(0.015)
      .pointRadius('radius')
      .pointColor('color')
      .pointLabel('label')
      .onPointClick(p => {
        if (p?.kind === 'event' || p?.kind === 'iran') onSelectEvent?.(p.data);
      });

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
