import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePolling, useFilters } from './usePolling';

describe('usePolling', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('fetches immediately on mount', async () => {
    const fn = vi.fn().mockResolvedValue({ v: 1 });
    const { result } = renderHook(() => usePolling(fn, 30000));
    await act(async () => { await Promise.resolve(); });
    expect(fn).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual({ v: 1 });
  });

  it('exposes the error message and keeps polling', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('boom'));
    const { result } = renderHook(() => usePolling(fn, 1000));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.error).toBe('boom');
  });

  it('clears a previous error once a fetch succeeds again', async () => {
    const fn = vi.fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValue({ v: 2 });
    const { result } = renderHook(() => usePolling(fn, 1000));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.error).toBe('boom');

    await act(async () => { await result.current.refetch(); });
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual({ v: 2 });
  });

  it('ignores a slow response that resolves after a newer one (sequence guard)', async () => {
    let resolveSlow;
    const slow = new Promise(res => { resolveSlow = res; });
    const fn = vi.fn()
      .mockReturnValueOnce(slow)                    // الأول: بطيء
      .mockResolvedValueOnce({ v: 'fresh' });       // الثاني: أسرع

    const { result } = renderHook(() => usePolling(fn, 100000));

    // أطلق طلباً ثانياً قبل أن يعود الأول
    await act(async () => { await result.current.refetch(); });
    expect(result.current.data).toEqual({ v: 'fresh' });

    // الآن يعود الطلب القديم — يجب ألا يكتب فوق الأحدث
    await act(async () => { resolveSlow({ v: 'stale' }); await Promise.resolve(); });
    expect(result.current.data).toEqual({ v: 'fresh' });
  });

  it('marks data stale and loading while a changed window loads, keeping the old data', async () => {
    let resolveNew;
    const fn = vi.fn((h) => (h === 48 ? Promise.resolve({ h }) : new Promise(res => { resolveNew = () => res({ h }); })));
    const { result, rerender } = renderHook(({ h }) => usePolling(() => fn(h), 100000, [h]), { initialProps: { h: 48 } });
    await act(async () => { await Promise.resolve(); });
    expect(result.current).toMatchObject({ data: { h: 48 }, stale: false, loading: false });

    rerender({ h: 168 });
    // البيانات السابقة باقية (لا وميض)، لكنها معلَّمة قديمة
    expect(result.current).toMatchObject({ data: { h: 48 }, stale: true, loading: true });

    await act(async () => { resolveNew(); await Promise.resolve(); });
    expect(result.current).toMatchObject({ data: { h: 168 }, stale: false, loading: false });
  });

  it('keeps the stale flag with the error when the new window fails', async () => {
    const fn = vi.fn((h) => (h === 48 ? Promise.resolve({ h }) : Promise.reject(new Error('down'))));
    const { result, rerender } = renderHook(({ h }) => usePolling(() => fn(h), 100000, [h]), { initialProps: { h: 48 } });
    await act(async () => { await Promise.resolve(); });
    rerender({ h: 168 });
    await act(async () => { await Promise.resolve(); });
    expect(result.current).toMatchObject({ data: { h: 48 }, stale: true, error: 'down', loading: false });
  });

  it('does not mark data stale on a periodic refetch', async () => {
    const fn = vi.fn().mockResolvedValueOnce({ v: 1 }).mockRejectedValue(new Error('blip'));
    const { result } = renderHook(() => usePolling(fn, 1000, ['same']));
    await act(async () => { await Promise.resolve(); });
    await act(async () => { vi.advanceTimersByTime(1000); await Promise.resolve(); });
    expect(result.current).toMatchObject({ data: { v: 1 }, stale: false, error: 'blip' });
  });

  it('skips the interval tick while the tab is hidden', async () => {
    const fn = vi.fn().mockResolvedValue({});
    const spy = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');

    renderHook(() => usePolling(fn, 1000));
    await act(async () => { await Promise.resolve(); });
    expect(fn).toHaveBeenCalledTimes(1);           // الجلب الأولي يحدث دائماً

    await act(async () => { vi.advanceTimersByTime(3000); });
    expect(fn).toHaveBeenCalledTimes(1);           // لا استطلاع أثناء الإخفاء

    spy.mockReturnValue('visible');
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(fn).toHaveBeenCalledTimes(2);
  });
});

describe('useFilters', () => {
  it('starts with sane defaults', () => {
    const { result } = renderHook(() => useFilters());
    expect(result.current.filters.hours).toBe(24);
    expect(result.current.filters.search).toBe('');
  });

  it('updates a single key without touching the others', () => {
    const { result } = renderHook(() => useFilters());
    act(() => result.current.updateFilter('category', 'military'));
    expect(result.current.filters.category).toBe('military');
    expect(result.current.filters.hours).toBe(24);
  });

  it('resets every filter back to the defaults', () => {
    const { result } = renderHook(() => useFilters());
    act(() => result.current.updateFilter('category', 'military'));
    act(() => result.current.updateFilter('hours', 72));
    act(() => result.current.resetFilters());
    expect(result.current.filters.category).toBe('');
    expect(result.current.filters.hours).toBe(24);
  });
});
