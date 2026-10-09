/**
 * رصد - خطافات مخصصة
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { IMPACT_SECTORS, TIME_WINDOWS } from '../utils/constants';

/**
 * خطاف جلب البيانات مع تحديث تلقائي.
 *
 * يعيد `lastFetchedAt` أيضاً: وقت آخر استجابة معلومة يملكها هذا الخطاف، فيعرضه
 * الهيدر منها بدل اشتقاقه من تغيّر هوية كائن البيانات.
 *
 * عند تغيّر `deps` (نافذة زمنية، فلتر) تبقى البيانات السابقة معروضة كي لا تومض
 * القوائم فارغة مع كل ضغطة فلتر، لكن `stale` يصير true و`loading` يعود true حتى
 * تصل استجابة الطلب الجديد. فإن فشل بقي `stale` مع `error`: المكوّن يعرف أن ما
 * يعرضه يخص الفترة السابقة لا المختارة.
 */
export function usePolling(fetchFn, interval = 30000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stale, setStale] = useState(false);
  const [lastFetchedAt, setLastFetchedAt] = useState(null);
  const intervalRef = useRef(null);
  const fetchRef = useRef(fetchFn);

  useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  // حارس تسلسل: يمنع استجابة قديمة (شبكة بطيئة) من الكتابة فوق أحدث منها
  const seqRef = useRef(0);

  const run = useCallback(async (depsChanged = false) => {
    const mySeq = ++seqRef.current;
    if (depsChanged) {
      setLoading(true);
      setStale(true);
    }
    try {
      const result = await fetchRef.current();
      if (mySeq !== seqRef.current) return; // وصلت استجابة أحدث — تجاهل هذه
      setData(result);
      setError(null);
      setStale(false);
      setLastFetchedAt(new Date());
    } catch (err) {
      if (mySeq !== seqRef.current) return;
      setError(err.message);
    } finally {
      if (mySeq === seqRef.current) setLoading(false);
    }
  }, []);

  const refetch = useCallback(() => run(false), [run]);

  // مقارنة سطحية بآخر deps: التأثير يُعاد أيضًا عند تغيّر interval أو في
  // StrictMode، وهذان لا يجعلان البيانات المعروضة قديمة.
  const prevDepsRef = useRef(deps);

  // يُعاد الجلب فورًا عند تغيّر deps (مثل الفلاتر) لا فقط في الدورة التالية.
  // كما نوقف الاستطلاع عندما يكون التبويب مخفياً (توفير شبكة/معالج) ونجلب فوراً
  // عند العودة إليه.
  useEffect(() => {
    const prev = prevDepsRef.current;
    const depsChanged = prev.length !== deps.length || deps.some((d, i) => !Object.is(d, prev[i]));
    prevDepsRef.current = deps;

    const tick = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      run(false);
    };
    run(depsChanged);
    intervalRef.current = setInterval(tick, interval);

    const onVisible = () => {
      if (document.visibilityState === 'visible') run(false);
    };
    document.addEventListener('visibilitychange', onVisible);

    return () => {
      clearInterval(intervalRef.current);
      document.removeEventListener('visibilitychange', onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, interval, ...deps]);

  return { data, loading, error, stale, lastFetchedAt, refetch };
}

// ===== الفلاتر =====

const FILTER_DEFAULTS = {
  category: '',
  severity: '',
  country_code: '',
  source: '',
  search: '',
  sector: '',
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
  // قطاع غير معروف يعيد 422 من الخادم — نُسقطه بدل كسر القائمة
  if (key === 'sector') return IMPACT_SECTORS[raw] ? raw : '';
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
 * ضبط "عسكري + إيران + 72 ساعة" يبقى بعد إعادة التحميل ويُشارَك برابط.
 * نقرأ من العنوان عند التركيب ونكتب بـ replaceState عند كل تغيير (لا pushState:
 * وإلا صارت كل ضغطة مرشّح خطوة في تاريخ المتصفح).
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
