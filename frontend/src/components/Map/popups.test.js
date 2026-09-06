/**
 * اختبارات قوالب نوافذ الخريطة.
 *
 * القوالب تُحقن في innerHTML عبر Leaflet، وبياناتها تأتي من خلاصات RSS/OSINT
 * خارجية غير موثوقة. هذه الاختبارات تحرس التهريب ورفض الروابط الخطرة — وهي
 * لم تكن قابلة للاختبار أصلاً حين كانت القوالب سلاسل داخل تأثيرات المكوّن.
 */
import { describe, it, expect } from 'vitest';
import {
  basePopup, clusterPopup, eventPopup, flightPopup, iranPopup, nuclearPopup, pipelinePopup,
} from './popups';

// t وهمية: تُعيد defaultValue إن وُجد وإلا المفتاح نفسه
const t = (key, opts) => opts?.defaultValue ?? key;
const ctx = { t, dir: 'rtl' };

const XSS = '<img src=x onerror="alert(1)">';

describe('تهريب المحتوى الخارجي', () => {
  it('يهرّب عنوان الحدث فلا يصير وسماً', () => {
    const html = eventPopup({ title: XSS, category: 'military', severity: 'high' }, ctx);
    expect(html).not.toContain('<img src=x');
    expect(html).toContain('&lt;img');
  });

  it('يهرّب وصف الضربة وعنوانها', () => {
    const html = iranPopup({ title: XSS, description: XSS, confidence: 'HIGH' }, ctx);
    expect(html).not.toContain('onerror="alert(1)"');
  });

  it('يهرّب عناوين المجموعة', () => {
    const html = clusterPopup({ events: [{ id: 1, title: XSS, category: 'general' }] }, ctx);
    expect(html).not.toContain('<img src=x');
  });

  it('يهرّب ملاحظات القاعدة العسكرية', () => {
    const html = basePopup({ name_ar: 'قاعدة', notes: XSS }, ctx);
    expect(html).not.toContain('<img src=x');
  });

  it('يهرّب إشارة نداء الطائرة', () => {
    const html = flightPopup({ callsign: XSS, is_military: true }, ctx);
    expect(html).not.toContain('<img src=x');
  });
});

describe('تعقيم الروابط', () => {
  it('يُسقط رابط javascript: من الحدث', () => {
    const html = eventPopup(
      { title: 'خبر', url: 'javascript:alert(1)', category: 'general', severity: 'low' },
      ctx,
    );
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('<a href');
  });

  it('يُسقط رابط فيديو data: من ضربة إيران', () => {
    const html = iranPopup(
      { title: 'ضربة', video_url: 'data:text/html,<script>x</script>', confidence: 'LOW' },
      ctx,
    );
    expect(html).not.toContain('data:text/html');
  });

  it('يُبقي روابط https ويضيف rel آمناً', () => {
    const html = eventPopup(
      { title: 'خبر', url: 'https://example.test/a', category: 'general', severity: 'low' },
      ctx,
    );
    expect(html).toContain('https://example.test/a');
    expect(html).toContain('rel="noopener noreferrer"');
  });
});

describe('الاتجاه والبنية', () => {
  it('يتبع اتجاه الواجهة لا قيمة ثابتة', () => {
    const data = { title: 'x', category: 'general', severity: 'low' };
    expect(eventPopup(data, { t, dir: 'ltr' })).toContain('direction:ltr');
    expect(eventPopup(data, { t, dir: 'rtl' })).toContain('direction:rtl');
  });

  it('يعرض حقول المنشأة النووية الاختيارية فقط عند وجودها', () => {
    const base = { name_ar: 'نطنز', type: 'enrichment', status: 'operational', latitude: 33.7, longitude: 51.7 };
    const without = nuclearPopup(base, { ...ctx, typeColor: '#fff', statusColor: '#0f0' });
    const with_ = nuclearPopup({ ...base, capacity_mw: 1000 }, { ...ctx, typeColor: '#fff', statusColor: '#0f0' });

    expect(without).not.toContain('MW');
    expect(with_).toContain('1000 MW');
  });

  it('يختار وحدة سعة الأنبوب حسب نوعه', () => {
    const oil = pipelinePopup({ type: 'oil', name_ar: 'أ', capacity_mbpd: 5 }, { ...ctx, color: '#fff' });
    const gas = pipelinePopup({ type: 'gas', name_ar: 'ب', capacity_bcm: 9 }, { ...ctx, color: '#fff' });

    expect(oil).toContain('map.mbpd');
    expect(gas).toContain('map.bcm');
  });
});
