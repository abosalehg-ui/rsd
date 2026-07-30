/**
 * اختبارات إزاحة العلامات المتراكبة عبر الطبقات.
 *
 * السيناريو الذي تحرسه: ضربة 💥 ومنشأة ☢️ ومجموعة أحداث على الإحداثيات نفسها
 * — كانت تُرسم فوق بعضها تماماً فتُحجب إحداها عن النقر.
 */
import { describe, it, expect } from 'vitest';
import { computeMarkerNudges, Z_OFFSET } from './RasadMap';

const LAT = 24.7136;
const LNG = 46.6753;
const ZOOM = 5;

describe('computeMarkerNudges', () => {
  it('لا يزيح العلامات المتباعدة', () => {
    const nudges = computeMarkerNudges([
      { key: 'ev:0', kind: 'event', lat: LAT, lng: LNG },
      { key: 'ir:1', kind: 'iran', lat: 21.54, lng: 39.17 },
    ], ZOOM);
    expect(nudges.size).toBe(0);
  });

  it('يوزّع العلامات المتطابقة الموقع على مواضع متمايزة', () => {
    const nudges = computeMarkerNudges([
      { key: 'ev:0', kind: 'event', lat: LAT, lng: LNG },
      { key: 'ir:901', kind: 'iran', lat: LAT, lng: LNG },
      { key: 'nu:5', kind: 'nuclear', lat: LAT, lng: LNG },
    ], ZOOM);

    expect(nudges.size).toBe(3);
    const positions = [...nudges.values()].map(v => `${v.dx.toFixed(2)},${v.dy.toFixed(2)}`);
    expect(new Set(positions).size).toBe(3);   // لا موضعين متطابقين

    // كل علامة أُزيحت فعلاً بعيداً عن المركز
    for (const { dx, dy } of nudges.values()) {
      expect(Math.hypot(dx, dy)).toBeGreaterThan(10);
    }
  });

  it('يمنح الضربة 💥 الموضع العلوي فوق نقطة الحدث', () => {
    const nudges = computeMarkerNudges([
      { key: 'ev:0', kind: 'event', lat: LAT, lng: LNG },
      { key: 'ir:901', kind: 'iran', lat: LAT, lng: LNG },
    ], ZOOM);
    // أولوية iran أعلى ⇒ تأخذ أول موضع في الحلقة (للأعلى: dy سالب)
    expect(nudges.get('ir:901').dy).toBeLessThan(0);
    expect(nudges.get('ev:0').dy).toBeGreaterThan(0);
  });

  it('يفكّ التراكب عند التقريب دون إزاحة حين تتباعد النقاط فعلاً', () => {
    const items = [
      { key: 'ev:0', kind: 'event', lat: LAT, lng: LNG },
      { key: 'ir:901', kind: 'iran', lat: LAT + 0.02, lng: LNG + 0.02 },
    ];
    // متقاربة بصرياً عند التصغير ⇒ تُزاح
    expect(computeMarkerNudges(items, 5).size).toBe(2);
    // متباعدة بصرياً عند التقريب ⇒ لا حاجة للإزاحة
    expect(computeMarkerNudges(items, 13).size).toBe(0);
  });

  it('يرتّب الطبقات: الضربات فوق المنشآت فوق الأحداث، والطيران أدناها', () => {
    expect(Z_OFFSET.iran).toBeGreaterThan(Z_OFFSET.nuclear);
    expect(Z_OFFSET.nuclear).toBeGreaterThan(Z_OFFSET.base);
    expect(Z_OFFSET.base).toBeGreaterThan(Z_OFFSET.event);
    expect(Z_OFFSET.flight).toBeLessThan(Z_OFFSET.event);
  });
});
