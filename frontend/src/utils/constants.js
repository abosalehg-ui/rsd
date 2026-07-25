/**
 * رصد - ثوابت ومساعدات
 *
 * هذا الملف يحمل البيانات **البنيوية** فقط (ألوان، أيقونات، أعلام). كل النصوص
 * المعروضة تأتي من i18next عبر المفاتيح المقابلة:
 *   categories.<key> · severity.<key> · countries.<code> ·
 *   confidence.<LEVEL> · iranEventTypes.<type>
 * كانت التسميات مكتوبة عربية حرفياً هنا فتظهر بالعربية حتى في الوضع الإنجليزي.
 *
 * ملاحظة على الألوان: رُفعت درجات النص الثانوي درجةً واحدة (مثل #ef4444 →
 * #f87171) لتجاوز حدّ التباين 4.5:1 على الخلفية الداكنة #0d1117.
 */

export const CATEGORIES = {
  military: { icon: '💥', color: '#f87171', bg: 'bg-red-500/20', text: 'text-red-300' },
  diplomatic: { icon: '🤝', color: '#60a5fa', bg: 'bg-blue-500/20', text: 'text-blue-300' },
  humanitarian: { icon: '🆘', color: '#fb923c', bg: 'bg-orange-500/20', text: 'text-orange-300' },
  nuclear: { icon: '☣️', color: '#facc15', bg: 'bg-yellow-500/20', text: 'text-yellow-300' },
  economic: { icon: '📊', color: '#34d399', bg: 'bg-emerald-500/20', text: 'text-emerald-300' },
  general: { icon: '📰', color: '#94a3b8', bg: 'bg-slate-500/20', text: 'text-slate-300' },
};

export const SEVERITIES = {
  critical: { color: '#f87171', bg: 'bg-red-500', dot: '🔴' },
  high: { color: '#fb923c', bg: 'bg-orange-500', dot: '🟠' },
  medium: { color: '#facc15', bg: 'bg-yellow-500', dot: '🟡' },
  low: { color: '#34d399', bg: 'bg-emerald-500', dot: '🟢' },
};

export const COUNTRIES = {
  PS: { flag: '🇵🇸' },
  IL: { flag: '🇮🇱' },
  YE: { flag: '🇾🇪' },
  SY: { flag: '🇸🇾' },
  LB: { flag: '🇱🇧' },
  IR: { flag: '🇮🇷' },
  IQ: { flag: '🇮🇶' },
  SA: { flag: '🇸🇦' },
  EG: { flag: '🇪🇬' },
  JO: { flag: '🇯🇴' },
  TR: { flag: '🇹🇷' },
  LY: { flag: '🇱🇾' },
  SD: { flag: '🇸🇩' },
};

// Iran OSINT - تصنيف الثقة
export const CONFIDENCE = {
  HIGH: { color: '#4ade80', icon: '🟢', bg: 'bg-green-500/20', text: 'text-green-300' },
  MEDIUM: { color: '#facc15', icon: '🟡', bg: 'bg-yellow-500/20', text: 'text-yellow-300' },
  LOW: { color: '#60a5fa', icon: '🔵', bg: 'bg-blue-500/20', text: 'text-blue-300' },
};

// أنواع أحداث إيران
export const IRAN_EVENT_TYPES = {
  strike: { icon: '💥', color: '#f87171' },
  launch: { icon: '🚀', color: '#fb923c' },
  movement: { icon: '🪖', color: '#a78bfa' },
  nuclear: { icon: '☢️', color: '#facc15' },
  diplomatic: { icon: '🤝', color: '#60a5fa' },
};

// النوافذ الزمنية المتاحة (بالساعات) — مصدر واحد للوحة الأخبار والخط الزمني،
// فلا يعرض الخط الزمني نافذة أوسع من البيانات المجلوبة فعلاً.
export const TIME_WINDOWS = [6, 12, 24, 48, 72, 168];

// المصادر المتاحة للفلترة (تطابق قيم Event.source في الخلفية)
export const SOURCES = ['gdelt', 'newsapi', 'rss', 'ucdp', 'iran_osint'];

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
