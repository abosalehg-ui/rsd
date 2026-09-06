/**
 * رصد - خطافات مخصصة
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { TIME_WINDOWS } from '../utils/constants';

/**
 * خطاف جلب البيانات مع تحديث تلقائي.
 *
 * يعيد `lastFetchedAt` أيضاً: كان الهيدر يشتقّ "وقت آخر فحص" من تغيّر هوية
 * كائن البيانات داخل تأثير مع `setTimeout(…, 0)` للالتفاف على دورة عرض
 * متتالية. الوقت معلومة يملكها هذا الخطاف أصلاً، فنُعيدها صراحةً.
 */
export function usePolling(fetchFn, interval = 30000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastFetchedAt, setLastFetchedAt] = useState(null);
  const intervalRef = useRef(null);
  const fetchRef = useRef(fetchFn);

  useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  // حارس تسلسل: يمنع استجابة قديمة (شبكة بطيئة) من الكتابة فوق أحدث منها
  const seqRef = useRef(0);

  const doFetch = useCallback(async () => {
    const mySeq = ++seqRef.current;
    try {
      const result = await fetchRef.current();
      if (mySeq !== seqRef.current) return; // وصلت استجابة أحدث — تجاهل هذه
      setData(result);
      setError(null);
      setLastFetchedAt(new Date());
    } catch (err) {
      if (mySeq !== seqRef.current) return;
      setError(err.message);
    } finally {
      if (mySeq === seqRef.current) setLoading(false);
    }
  }, []);

  // يُعاد الجلب فورًا عند تغيّر deps (مثل الفلاتر) لا فقط في الدورة التالية.
  // كما نوقف الاستطلاع عندما يكون التبويب مخفياً (توفير شبكة/معالج) ونجلب فوراً
  // عند العودة إليه.
  useEffect(() => {
    const tick = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      doFetch();
    };
    doFetch();
    intervalRef.current = setInterval(tick, interval);

    const onVisible = () => {
      if (document.visibilityState === 'visible') doFetch();
    };
    document.addEventListener('visibilitychange', onVisible);

    return () => {
      clearInterval(intervalRef.current);
      document.removeEventListener('visibilitychange', onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doFetch, interval, ...deps]);

  return { data, loading, error, lastFetchedAt, refetch: doFetch };
}

// ===== الفلاتر =====

const FILTER_DEFAULTS = {
  category: '',
  severity: '',
  country_code: '',
  source: '',
  search: '',
  hours: 24,
};

// حدود الخادم (`api/events.py`): تجاوزها يعيد 422 بدل نتائج. عنوان يكتبه
// المستخدم بيده لا يجوز أن يُسقط اللوحة، فنُطهّر القيم قبل استعمالها.
const SEARCH_MAX = 100;

function sanitize(key, raw) {
  if (key === 'hours') {
    const n = Number(raw);
    return TIME_WINDOWS.includes(n) ? n : FILTER_DEFAULTS.hours;
  }
  return String(raw ?? '').slice(0, SEARCH_MAX);
}

function readFiltersFromUrl(initial) {
  const base = { ...FILTER_DEFAULTS, ...initial };
  if (typeof window === 'undefined') return base;
  try {
    const params = new URLSearchParams(window.location.search);
    Object.keys(FILTER_DEFAULTS).forEach(key => {
      if (params.has(key)) base[key] = sanitize(key, params.get(key));
    });
  } catch { /* بيئة بلا window.location قابلة للتحليل */ }
  return base;
}

function writeFiltersToUrl(filters) {
  if (typeof window === 'undefined' || !window.history?.replaceState) return;
  try {
    const params = new URLSearchParams(window.location.search);
    Object.entries(FILTER_DEFAULTS).forEach(([key, fallback]) => {
      const value = filters[key];
      if (value === fallback || value === '' || value == null) params.delete(key);
      else params.set(key, String(value));
    });
    const query = params.toString();
    window.history.replaceState(null, '', query
      ? `${window.location.pathname}?${query}`
      : window.location.pathname);
  } catch { /* تجاهل — الفلاتر تعمل بدون العنوان */ }
}

/**
 * خطاف الفلاتر — الحالة منعكسة في عنوان الصفحة.
 *
 * كان ضبط "عسكري + إيران + 72 ساعة" يضيع مع أول إعادة تحميل ولا يمكن مشاركته.
 * نقرأ من العنوان عند التركيب ونكتب بـ replaceState عند كل تغيير (لا pushState:
 * كل ضغطة مرشّح كانت ستصير خطوة في تاريخ المتصفح).
 */
export function useFilters(initialFilters = {}) {
  const [filters, setFilters] = useState(() => readFiltersFromUrl(initialFilters));

  useEffect(() => {
    writeFiltersToUrl(filters);
  }, [filters]);

  const updateFilter = useCallback((key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ ...FILTER_DEFAULTS });
  }, []);

  return { filters, updateFilter, resetFilters };
}
