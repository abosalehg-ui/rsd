/**
 * رصد - ثوابت ومساعدات
 */

export const CATEGORIES = {
  military: { label: 'عسكري', icon: '💥', color: '#ef4444', bg: 'bg-red-500/20', text: 'text-red-400' },
  diplomatic: { label: 'دبلوماسي', icon: '🤝', color: '#3b82f6', bg: 'bg-blue-500/20', text: 'text-blue-400' },
  humanitarian: { label: 'إنساني', icon: '🆘', color: '#f97316', bg: 'bg-orange-500/20', text: 'text-orange-400' },
  nuclear: { label: 'نووي', icon: '☣️', color: '#eab308', bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  economic: { label: 'اقتصادي', icon: '📊', color: '#10b981', bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
  general: { label: 'عام', icon: '📰', color: '#64748b', bg: 'bg-slate-500/20', text: 'text-slate-400' },
};

export const SEVERITIES = {
  critical: { label: 'حرج', color: '#ef4444', bg: 'bg-red-500', dot: '🔴' },
  high: { label: 'مرتفع', color: '#f97316', bg: 'bg-orange-500', dot: '🟠' },
  medium: { label: 'متوسط', color: '#eab308', bg: 'bg-yellow-500', dot: '🟡' },
  low: { label: 'منخفض', color: '#10b981', bg: 'bg-emerald-500', dot: '🟢' },
};

export const COUNTRIES = {
  PS: { name: 'فلسطين', flag: '🇵🇸' },
  IL: { name: 'إسرائيل', flag: '🇮🇱' },
  YE: { name: 'اليمن', flag: '🇾🇪' },
  SY: { name: 'سوريا', flag: '🇸🇾' },
  LB: { name: 'لبنان', flag: '🇱🇧' },
  IR: { name: 'إيران', flag: '🇮🇷' },
  IQ: { name: 'العراق', flag: '🇮🇶' },
  SA: { name: 'السعودية', flag: '🇸🇦' },
  EG: { name: 'مصر', flag: '🇪🇬' },
  JO: { name: 'الأردن', flag: '🇯🇴' },
  TR: { name: 'تركيا', flag: '🇹🇷' },
  LY: { name: 'ليبيا', flag: '🇱🇾' },
  SD: { name: 'السودان', flag: '🇸🇩' },
};

export function timeAgo(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);

  if (diff < 60) return 'الآن';
  if (diff < 3600) return `منذ ${Math.floor(diff / 60)} دقيقة`;
  if (diff < 86400) return `منذ ${Math.floor(diff / 3600)} ساعة`;
  return `منذ ${Math.floor(diff / 86400)} يوم`;
}

export function formatNumber(num) {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num?.toString() || '0';
}
