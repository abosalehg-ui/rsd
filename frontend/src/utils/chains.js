/**
 * رصد - مساعدات عرض سلاسل السبب والأثر (روابط قاعدية من الخادم).
 *
 * دوال نقيّة: مستوى الثقة ولونه، والنسبة المئوية، ونص العلاقة واسم الكيان
 * باللغة المختارة. الألوان من مقياس الخطورة في `constants` (لا hex هنا).
 */
import { SEVERITIES } from './constants';

/** دون هذه الثقة يُعدّ الرابط «ضعيفًا» ويخفيه مفتاح «إخفاء ضعيفة الثقة». */
export const LOW_CONFIDENCE = 0.55;
export const HIGH_CONFIDENCE = 0.7;

export function confidenceLevel(value) {
  const v = Number(value) || 0;
  if (v >= HIGH_CONFIDENCE) return 'high';
  if (v >= LOW_CONFIDENCE) return 'medium';
  return 'low';
}

// ثقة مرتفعة = أخضر الخطورة المنخفضة، وضعيفة = برتقالي الخطورة المرتفعة
const LEVEL_COLOR = { high: 'low', medium: 'medium', low: 'high' };

export function confidenceColor(value) {
  return SEVERITIES[LEVEL_COLOR[confidenceLevel(value)]].color;
}

export function pct(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

export function relationText(link, lang) {
  return (lang === 'ar' ? link?.relation_ar : link?.relation_en) || link?.relation_en || '';
}

export function entityName(entity, lang) {
  return (lang === 'ar' ? entity?.ar : entity?.en) || entity?.key || '';
}

/** «0.62 = 0.85 × 0.85 × 1 × 0.9» — أرقام المعادلة كما خزّنها الخادم. */
export function confidenceFormula(link) {
  const c = link?.evidence?.components;
  if (!c) return '';
  const n = (v) => String(Number((Number(v) || 0).toFixed(3)));
  return `${n(link.confidence)} = ${[c.template, c.entity, c.time, c.source_trust].map(n).join(' × ')}`;
}
