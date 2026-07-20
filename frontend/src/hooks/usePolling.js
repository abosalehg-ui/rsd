/**
 * رصد - خطافات مخصصة
 */
import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * خطاف جلب البيانات مع تحديث تلقائي
 */
export function usePolling(fetchFn, interval = 30000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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

  return { data, loading, error, refetch: doFetch };
}

/**
 * خطاف الفلاتر
 */
export function useFilters(initialFilters = {}) {
  const [filters, setFilters] = useState({
    category: '',
    severity: '',
    country_code: '',
    source: '',
    search: '',
    hours: 24,
    ...initialFilters,
  });

  const updateFilter = useCallback((key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      category: '',
      severity: '',
      country_code: '',
      source: '',
      search: '',
      hours: 24,
    });
  }, []);

  return { filters, updateFilter, resetFilters };
}
