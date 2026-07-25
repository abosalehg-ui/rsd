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
