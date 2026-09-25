/**
 * رصد - ثوابت ومساعدات
 *
 * هذا الملف يحمل البيانات **البنيوية** فقط (ألوان، أيقونات، أعلام). كل النصوص
 * المعروضة تأتي من i18next عبر المفاتيح المقابلة — لا تسميات حرفية هنا:
 *   categories.<key> · severity.<key> · countries.<code> ·
 *   confidence.<LEVEL> · iranEventTypes.<type>
 *
 * ملاحظة على الألوان: رُفعت درجات النص الثانوي درجةً واحدة (مثل #ef4444 →
 * #f87171) لتجاوز حدّ التباين 4.5:1 على الخلفية الداكنة #0d1117.
 */

/**
 * ألوان الثيم لقوالب HTML الخام (نوافذ Leaflet وتسميات globe.gl).
 *
 * تلك القوالب سلاسل نصية لا JSX، فلا تصلها أصناف Tailwind ولا متغيّرات CSS.
 * كانت قيم hex مكتوبة يدويًا داخل كل قالب، فأي تغيير للثيم يترك النوافذ
 * بالألوان القديمة. هذا هو المصدر الواحد لها — ويطابق رموز `tailwind.config.js`.
 */
export const THEME = {
  bg: '#0b1016',        // rasad-bg
  panel: '#121a22',     // rasad-panel
  border: '#22303c',    // rasad-border
  text: '#e2e8f0',      // نص أساسي داخل النوافذ
  textSecondary: '#cbd5e1',
  textMuted: '#94a3b8',
  accent: '#67e8f9',    // روابط وعناوين
  highlight: '#fbbf24', // قيم مُبرَزة (سعة، مُشغّل)
  violet: '#a78bfa',    // القواعد العسكرية
  violetSoft: '#c4b5fd',
};

// الأيقونات أسماء مكوّنات lucide (انظر utils/icons.jsx) لا رموز تعبيرية: كانت
// الواجهة تخلط الإيموجي بأيقونات الخطوط فيتفاوت حجمها ولونها بين الأنظمة.
// النووي بلون الخطر الأصفر (لون رمز الإشعاع)، والإشعاعي بالأرجواني التقليدي
// لعلامات الإشعاع — مجالا الرصد الأساسيان بلونين لا يستعملهما غيرهما.
export const CATEGORIES = {
  nuclear: { icon: 'atom', color: '#f2c230' },
  radiological: { icon: 'radiation', color: '#e0609c' },
  military: { icon: 'swords', color: '#f87171' },
  diplomatic: { icon: 'handshake', color: '#60a5fa' },
  humanitarian: { icon: 'heart', color: '#fb923c' },
  economic: { icon: 'trend', color: '#34d399' },
  general: { icon: 'news', color: '#94a3b8' },
};

export const SEVERITIES = {
  critical: { color: '#f4585d' },
  high: { color: '#f08a3c' },
  medium: { color: '#e8c547' },
  low: { color: '#5fb38a' },
};

/** الموضوعات النووية/الإشعاعية (backend/app/processors/nuclear.TOPICS). */
export const NUCLEAR_TOPICS = {
  radiation_release: { category: 'radiological', base: 80 },
  military_threat: { category: 'nuclear', base: 75 },
  radioactive_source: { category: 'radiological', base: 62 },
  trafficking_security: { category: 'nuclear', base: 60 },
  safety_incident: { category: 'nuclear', base: 55 },
  weapons_program: { category: 'nuclear', base: 50 },
  safeguards_iaea: { category: 'nuclear', base: 35 },
  diplomacy_sanctions: { category: 'nuclear', base: 30 },
  emergency_preparedness: { category: 'radiological', base: 20 },
  regulatory: { category: 'nuclear', base: 15 },
  medical_industrial: { category: 'radiological', base: 12 },
  energy_program: { category: 'nuclear', base: 10 },
};

/** نطاقات درجة الخطر 0-100 — تطابق severity_from_score في الخلفية. */
export const RISK_BANDS = [
  { key: 'low', from: 0, to: 30 },
  { key: 'medium', from: 30, to: 55 },
  { key: 'high', from: 55, to: 75 },
  { key: 'critical', from: 75, to: 100 },
];

export function riskLevel(score) {
  const v = score || 0;
  if (v >= 75) return 'critical';
  if (v >= 55) return 'high';
  if (v >= 30) return 'medium';
  return 'low';
}

export const riskColor = (score) => SEVERITIES[riskLevel(score)].color;

/** اسم أقرب نقطة سعودية بلغة الواجهة (الخادم يعيد العربي و`_en`). */
export const ksaPlace = (obj, lang) =>
  (lang === 'ar' ? obj?.nearest_ksa_point : obj?.nearest_ksa_point_en || obj?.nearest_ksa_point) || '';

export const COUNTRIES = {
  SA: { flag: '🇸🇦' },
  AE: { flag: '🇦🇪' },
  QA: { flag: '🇶🇦' },
  KW: { flag: '🇰🇼' },
  BH: { flag: '🇧🇭' },
  OM: { flag: '🇴🇲' },
  PS: { flag: '🇵🇸' },
  IL: { flag: '🇮🇱' },
  YE: { flag: '🇾🇪' },
  SY: { flag: '🇸🇾' },
  LB: { flag: '🇱🇧' },
  IR: { flag: '🇮🇷' },
  IQ: { flag: '🇮🇶' },
  EG: { flag: '🇪🇬' },
  JO: { flag: '🇯🇴' },
  TR: { flag: '🇹🇷' },
  LY: { flag: '🇱🇾' },
  SD: { flag: '🇸🇩' },
  UA: { flag: '🇺🇦' },
  RU: { flag: '🇷🇺' },
  KP: { flag: '🇰🇵' },
  PK: { flag: '🇵🇰' },
  IN: { flag: '🇮🇳' },
  JP: { flag: '🇯🇵' },
};

// Iran OSINT - تصنيف الثقة
export const CONFIDENCE = {
  HIGH: { color: '#4ade80' },
  MEDIUM: { color: '#facc15' },
  LOW: { color: '#60a5fa' },
};

// أنواع أحداث إيران — الأيقونات أسماء من utils/icons.jsx
export const IRAN_EVENT_TYPES = {
  strike: { icon: 'flame', color: '#f87171' },
  launch: { icon: 'rocket', color: '#fb923c' },
  movement: { icon: 'shield', color: '#a78bfa' },
  nuclear: { icon: 'atom', color: '#f2c230' },
  diplomatic: { icon: 'handshake', color: '#60a5fa' },
};

// النوافذ الزمنية المتاحة (بالساعات) — مصدر واحد للوحة الأخبار والخط الزمني،
// فلا يعرض الخط الزمني نافذة أوسع من البيانات المجلوبة فعلاً.
export const TIME_WINDOWS = [6, 12, 24, 48, 72, 168];

// ===== مقياس ألوان موحّد للدرجات =====
// مصدر واحد للعتبات والألوان يستعمله الهيدر والإحصائيات ومؤشر الدول، كي لا
// يظهر المؤشر نفسه بلونين مختلفين في لوحتين.

// عتبات مؤشر التصعيد (نسبة مئوية 0-100)
export const ESCALATION_THRESHOLDS = { high: 30, medium: 15 };

// درجات لون متّسقة مع لوحة SEVERITIES (نفاذة التباين على الخلفية الداكنة)
const _RED = '#f87171';
const _ORANGE = '#fb923c';
const _AMBER = '#facc15';
const _GREEN = '#34d399';

/** لون مؤشر التصعيد (نسبة 0-100). */
export function escalationColor(pct) {
  const v = pct || 0;
  if (v > ESCALATION_THRESHOLDS.high) return _RED;
  if (v > ESCALATION_THRESHOLDS.medium) return _AMBER;
  return _GREEN;
}

/** لون درجة استخبارات الدولة (0-100، أربع مراتب). */
export function scoreColor(score) {
  const v = score || 0;
  if (v >= 75) return _RED;
  if (v >= 50) return _ORANGE;
  if (v >= 25) return _AMBER;
  return _GREEN;
}

// المصادر المتاحة للفلترة (تطابق قيم Event.source في الخلفية)
export const SOURCES = ['nuclear_watch', 'rss', 'gdelt', 'newsapi', 'ucdp', 'iran_osint'];

/** بحث آمن عن تصنيف — يقع على "general" للقيم غير المعروفة. */
export const categoryOf = (key) => CATEGORIES[key] || CATEGORIES.general;

/** بحث آمن عن خطورة — يقع على "low". */
export const severityOf = (key) => SEVERITIES[key] || SEVERITIES.low;

/**
 * صياغة "منذ كذا" بلغة الواجهة.
 * @param {string} dateStr تاريخ ISO
 * @param {Function} t دالة الترجمة من useTranslation()
 */
export function timeAgo(dateStr, t) {
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '';
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);

  if (diff < 60) return t('time.now');
  if (diff < 3600) return t('time.minutes', { count: Math.floor(diff / 60) });
  if (diff < 86400) return t('time.hours', { count: Math.floor(diff / 3600) });
  return t('time.days', { count: Math.floor(diff / 86400) });
}

export function formatNumber(num) {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num?.toString() || '0';
}
