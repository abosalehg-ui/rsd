/**
 * رصد - الكرة الأرضية ثلاثية الأبعاد (v1.3)
 *
 * تعرض نفس البيانات (أحداث / إيران / مفاعلات / قواعد / أنابيب) على كرة Three.js
 * عبر globe.gl. ليست بديلًا كاملاً عن خريطة Leaflet — وضع تكميلي.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Globe from 'globe.gl';
import { CATEGORIES, CONFIDENCE } from '../../utils/constants';
import { esc } from '../../utils/security';

const ME_LAT = 29.0;
const ME_LNG = 42.0;

// https صريح — الروابط النسبية للبروتوكول (//unpkg.com) تصير http عند التقديم
// عبر http (نشر docker المحلي) فتحجبها CSP (img-src https://unpkg.com فقط)
// وتبقى الكرة سوداء غير مرئية.
const GLOBE_IMG = 'https://unpkg.com/three-globe/example/img/earth-night.jpg';
const BUMP_IMG = 'https://unpkg.com/three-globe/example/img/earth-topology.png';

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

// حجم خلية التجميع (بالدرجات) حسب ارتفاع الكاميرا — كلما اقترب المستخدم صغُرت
// الخلية فتنفكّ المجموعات، مع حدّ أدنى يُبقي الأحداث متطابقة الإحداثيات مجمّعة.
function clusterGridDeg(altitude) {
  return Math.max(0.08, Math.min(8, altitude * 3.2));
}

// تجميع الأحداث المتقاربة كي لا تتراكب النقاط فيتعذّر الضغط على حدث بعينه
// (نفس مشكلة الخريطة 2D لكن على الكرة).
function clusterGlobeEvents(events, gridDeg) {
  const clusters = [];
  events.forEach(ev => {
    if (typeof ev.latitude !== 'number' || typeof ev.longitude !== 'number') return;
    let c = clusters.find(k =>
      Math.abs(k.lat / k.events.length - ev.latitude) < gridDeg &&
      Math.abs(k.lng / k.events.length - ev.longitude) < gridDeg
    );
    if (!c) {
      c = { lat: 0, lng: 0, events: [] };
      clusters.push(c);
    }
    c.events.push(ev);
    c.lat += ev.latitude;
    c.lng += ev.longitude;
  });
  return clusters.map(c => ({ lat: c.lat / c.events.length, lng: c.lng / c.events.length, events: c.events }));
}

export default function RasadGlobe({
  events = [],
  flights = null,
  iranStrikes = [],
  nuclearFacilities = [],
  bases = [],
  pipelines = [],
  onSelectEvent,
  layers = {},
  selectedEvent,
}) {
  // النصوص من i18n والاتجاه من لغة الواجهة — كان direction:rtl مثبّتاً وtooltip
  // الثقة يطبع undefined (CONFIDENCE بلا label، نُقلت للترجمة).
  const { t, i18n } = useTranslation();
  const dir = i18n.dir();
  // الطبقات مشتركة مع الخريطة 2D عبر App — كانت هنا افتراضات مستقلة (كلها true)
  // فتُعرض القواعد والأنابيب في وضع 3D بينما هي مُطفأة في 2D.
  const {
    events: showEvents = true,
    flights: showFlights = true,
    iran: showIran = true,
    nuclear: showNuclear = true,
    bases: showBases = false,
    pipelines: showPipelines = false,
  } = layers;
  const containerRef = useRef(null);
  const globeRef = useRef(null);
  // ارتفاع الكاميرا (مُقسّم إلى درجات متقطعة) — يعيد بناء التجميع عند تغيّر التقريب
  const [altBucket, setAltBucket] = useState(2); // يقابل altitude≈1.6 عند البداية
  const altRef = useRef(1.7);

  // إنشاء الكرة مرة واحدة
  useEffect(() => {
    if (!containerRef.current || globeRef.current) return;
    const container = containerRef.current;
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;

    const g = Globe()(container)
      .width(w)
      .height(h)
      .backgroundColor('#0a0e17')
      .globeImageUrl(GLOBE_IMG)
      .bumpImageUrl(BUMP_IMG)
      .atmosphereColor('#22d3ee')
      .atmosphereAltitude(0.18)
      .showGraticules(true);

    // إن تعذّر تحميل النسيج (انقطاع/حجب CSP) نُظهر كرة صلبة مرئية بدل سواد تام
    const probe = new Image();
    probe.crossOrigin = 'anonymous';
    probe.onerror = () => {
      try {
        g.globeImageUrl(null).bumpImageUrl(null);
        g.globeMaterial().color.set('#16324f');
      } catch { /* الكرة أُتلفت قبل اكتمال الفحص */ }
    };
    probe.src = GLOBE_IMG;

    g.pointOfView({ lat: ME_LAT, lng: ME_LNG, altitude: 1.7 }, 1500);

    // تعطيل auto-rotate تجنبًا للإرباك
    g.controls().autoRotate = false;
    g.controls().enableDamping = true;
    g.controls().dampingFactor = 0.1;

    // تتبّع الارتفاع بدرجات لوغاريتمية متقطعة كي لا نعيد بناء الطبقات مع كل إطار
    g.onZoom(({ altitude }) => {
      if (!altitude) return;
      altRef.current = altitude;
      const bucket = Math.round(Math.log2(altitude) * 3);
      setAltBucket(prev => (prev === bucket ? prev : bucket));
    });

    globeRef.current = g;

    // إعادة الحجم
    const ro = new ResizeObserver(() => {
      if (!containerRef.current || !globeRef.current) return;
      globeRef.current.width(containerRef.current.clientWidth);
      globeRef.current.height(containerRef.current.clientHeight);
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      try { globeRef.current?._destructor?.(); } catch { /* الكرة أُتلفت مسبقاً */ }
      container.innerHTML = '';
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
      const alt = Math.pow(2, altBucket / 3);
      const gridDeg = clusterGridDeg(alt);
      const eventPoint = (ev, lat, lng) => {
        const color = eventColor(ev);
        return {
          lat, lng, radius: pointRad(ev.severity), color,
          kind: 'event', data: ev,
          label: `<div style="direction:${dir};font-family:Tajawal,sans-serif;background:#111827;border:1px solid #1e293b;padding:6px 8px;border-radius:6px;max-width:280px">
            <div style="color:${color};font-size:11px;font-weight:700;margin-bottom:2px">${(CATEGORIES[ev.category]||CATEGORIES.general).icon} ${esc(ev.title)}</div>
            <div style="color:#94a3b8;font-size:10px">${esc(ev.country)}</div>
          </div>`,
        };
      };

      clusterGlobeEvents(events, gridDeg).forEach(cluster => {
        const hasCritical = cluster.events.some(e => e.severity === 'critical' || e.severity === 'high');
        if (cluster.events.length === 1) {
          const ev = cluster.events[0];
          points.push(eventPoint(ev, ev.latitude, ev.longitude));
        } else if (alt <= 0.5) {
          // قريب بما يكفي: ننشر النقاط المتطابقة على حلقة صغيرة (spiderfy)
          // كي يمكن تمييز كل حدث والضغط عليه.
          const spread = Math.max(0.04, gridDeg * 0.45);
          cluster.events.forEach((ev, i) => {
            const angle = (2 * Math.PI * i) / cluster.events.length;
            points.push(eventPoint(ev,
              cluster.lat + Math.sin(angle) * spread,
              cluster.lng + Math.cos(angle) * spread / Math.max(0.2, Math.cos(cluster.lat * Math.PI / 180))));
          });
        } else {
          // بعيد: نقطة تجميع واحدة بعدّاد — الضغط عليها يقرّب الكاميرا
          const color = hasCritical ? '#ef4444' : '#22d3ee';
          const titles = cluster.events.slice(0, 5)
            .map(e => `<div style="color:#cbd5e1;font-size:10px;padding:1px 0">${(CATEGORIES[e.category]||CATEGORIES.general).icon} ${esc((e.title || '').substring(0, 60))}</div>`)
            .join('');
          points.push({
            lat: cluster.lat, lng: cluster.lng,
            radius: Math.min(0.45 + cluster.events.length * 0.06, 1.1), color,
            kind: 'cluster', data: cluster,
            label: `<div style="direction:${dir};font-family:Tajawal,sans-serif;background:#111827;border:1px solid ${color};padding:6px 8px;border-radius:6px;max-width:280px">
              <div style="color:${color};font-size:11px;font-weight:700;margin-bottom:2px">${esc(t('map.clusterTitle', { count: cluster.events.length }))}</div>
              ${titles}
              <div style="color:#64748b;font-size:9px;margin-top:2px">${esc(t('globe.clusterZoomHint'))}</div>
            </div>`,
          });
        }
        const first = cluster.events.find(e => e.severity === 'critical') || cluster.events[0];
        if (hasCritical) {
          rings.push({ lat: cluster.lat, lng: cluster.lng, color: eventColor(first), maxR: first.severity === 'critical' ? 5 : 3.4, speed: 2.2, period: first.severity === 'critical' ? 900 : 1300 });
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
          label: `<div style="direction:${dir};font-family:Tajawal,sans-serif;background:#111827;border:1px solid ${conf.color};padding:6px 8px;border-radius:6px;max-width:280px">
            <div style="color:${conf.color};font-size:10px;margin-bottom:2px">${conf.icon} ${esc(t('confidence.' + s.confidence, { defaultValue: t('confidence.LOW') }))}</div>
            <div style="color:#fff;font-size:11px;font-weight:700">${esc(s.title)}</div>
          </div>`,
        });
        if (s.event_type === 'strike') {
          rings.push({ lat: s.latitude, lng: s.longitude, color: conf.color, maxR: 4.5, speed: 2.4, period: 1000 });
        }
      });
    }
    if (showFlights && flights?.flights) {
      flights.flights.forEach(f => {
        if (typeof f.latitude !== 'number' || typeof f.longitude !== 'number') return;
        const isMil = f.is_military;
        points.push({
          lat: f.latitude, lng: f.longitude, radius: isMil ? 0.3 : 0.18,
          color: isMil ? '#a855f7' : '#64748b', kind: 'flight', data: f,
          label: `<div style="direction:${dir};font-family:monospace;background:#0d1117;border:1px solid ${isMil ? '#a855f7' : '#475569'};padding:5px 7px;border-radius:6px">
            <div style="color:${isMil ? '#c4b5fd' : '#cbd5e1'};font-size:11px;font-weight:700">${isMil ? '⚔️ ' : '✈️ '}${esc(f.callsign || f.icao24 || '')}</div>
            <div style="color:#94a3b8;font-size:9px">${esc(f.origin_country || '')}</div>
          </div>`,
        });
      });
    }
    if (showNuclear) {
      nuclearFacilities.forEach(f => {
        if (typeof f.latitude !== 'number' || typeof f.longitude !== 'number') return;
        points.push({
          lat: f.latitude, lng: f.longitude, radius: f.type === 'power' ? 0.46 : 0.36, color: '#facc15',
          kind: 'nuclear', data: f,
          label: `<div style="direction:${dir};font-family:Tajawal,sans-serif;background:#0d1117;border:1px solid #facc15;padding:6px 8px;border-radius:6px;max-width:260px">
            <div style="color:#facc15;font-size:11px;font-weight:700">☢️ ${esc(f.name_ar || f.name_en)}</div>
            <div style="color:#94a3b8;font-size:9px">${esc(f.country || '')} • ${f.capacity_mw ? esc(f.capacity_mw) + ' MW' : esc(f.type)}</div>
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
          label: `<div style="direction:${dir};font-family:Tajawal,sans-serif;background:#0d1117;border:1px solid #a78bfa;padding:6px 8px;border-radius:6px;max-width:260px">
            <div style="color:#a78bfa;font-size:11px;font-weight:700">⚔️ ${esc(b.name_ar || b.name_en)}</div>
            <div style="color:#94a3b8;font-size:9px">${esc(b.country || '')} • ${esc(b.operator || '')}</div>
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
        if (p?.kind === 'event' || p?.kind === 'iran') {
          onSelectEvent?.(p.data);
        } else if (p?.kind === 'cluster') {
          // تقريب الكاميرا نحو المجموعة حتى تنفكّ إلى نقاط فردية
          g.pointOfView({ lat: p.lat, lng: p.lng, altitude: Math.max(0.35, altRef.current * 0.4) }, 800);
        }
      });

    g
      .ringsData(rings)
      .ringLat('lat')
      .ringLng('lng')
      .ringColor(d => (tt) => hexToRgba(d.color, 1 - tt))
      .ringMaxRadius('maxR')
      .ringPropagationSpeed('speed')
      .ringRepeatPeriod('period');
  }, [events, flights, iranStrikes, nuclearFacilities, bases, showEvents, showFlights, showIran, showNuclear, showBases, onSelectEvent, t, dir, altBucket]);

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
