/**
 * رصد - خطافات مخصصة
 */
import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * خطاف جلب البيانات مع تحديث تلقائي
 */
export function usePolling(fetchFn, interval = 30000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const fetchRef = useRef(fetchFn);

  useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  const doFetch = useCallback(async () => {
    try {
      const result = await fetchRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    doFetch();
    intervalRef.current = setInterval(doFetch, interval);
    return () => clearInterval(intervalRef.current);
  }, [doFetch, interval]);

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
