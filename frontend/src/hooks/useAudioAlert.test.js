import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { shouldAlert, loadAlertPrefs, saveAlertPrefs, useAudioAlert } from './useAudioAlert';

const prefs = (over = {}) => ({
  enabled: true,
  threshold: 'high',
  categories: [],
  desktopNotifications: false,
  throttleSeconds: 20,
  ...over,
});

describe('shouldAlert', () => {
  it('is silent when alerts are disabled', () => {
    expect(shouldAlert({ severity: 'critical' }, prefs({ enabled: false }))).toBe(false);
  });

  it('fires at or above the threshold', () => {
    expect(shouldAlert({ severity: 'high' }, prefs())).toBe(true);
    expect(shouldAlert({ severity: 'critical' }, prefs())).toBe(true);
  });

  it('stays silent below the threshold', () => {
    expect(shouldAlert({ severity: 'medium' }, prefs())).toBe(false);
    expect(shouldAlert({ severity: 'low' }, prefs())).toBe(false);
  });

  it('treats an unknown severity as below any threshold', () => {
    expect(shouldAlert({ severity: 'bogus' }, prefs({ threshold: 'low' }))).toBe(false);
  });

  it('is case-insensitive on severity', () => {
    expect(shouldAlert({ severity: 'CRITICAL' }, prefs())).toBe(true);
  });

  it('an empty category list means "all categories"', () => {
    expect(shouldAlert({ severity: 'critical', category: 'economic' }, prefs())).toBe(true);
  });

  it('filters by category when a list is set', () => {
    const p = prefs({ categories: ['military', 'nuclear'] });
    expect(shouldAlert({ severity: 'critical', category: 'military' }, p)).toBe(true);
    expect(shouldAlert({ severity: 'critical', category: 'economic' }, p)).toBe(false);
  });
});

describe('alert preferences persistence', () => {
  beforeEach(() => localStorage.clear());

  it('returns defaults when nothing is stored', () => {
    expect(loadAlertPrefs().threshold).toBe('high');
  });

  it('merges stored values over the defaults', () => {
    saveAlertPrefs({ threshold: 'critical' });
    const loaded = loadAlertPrefs();
    expect(loaded.threshold).toBe('critical');
    expect(loaded.enabled).toBe(true);       // من الافتراضيات
  });

  it('falls back to defaults on corrupt storage instead of throwing', () => {
    localStorage.setItem('rsd-alert-prefs', '{not json');
    expect(() => loadAlertPrefs()).not.toThrow();
    expect(loadAlertPrefs().threshold).toBe('high');
  });
});

describe('useAudioAlert baseline behaviour', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('does not alert for the events already present on first render', async () => {
    const initial = [{ id: 1, severity: 'critical', category: 'military', title: 'a' }];
    const { result } = renderHook(({ ev }) => useAudioAlert(ev, {}), {
      initialProps: { ev: initial },
    });
    await waitFor(() => expect(result.current.lastAlertEvent).toBeNull());
    expect(result.current.recentAlerts).toHaveLength(0);
  });

  it('alerts for a genuinely new event', async () => {
    const first = [{ id: 1, severity: 'critical', category: 'military', title: 'a' }];
    const { result, rerender } = renderHook(({ ev }) => useAudioAlert(ev, {}), {
      initialProps: { ev: first },
    });

    act(() => {
      rerender({ ev: [{ id: 2, severity: 'critical', category: 'military', title: 'b' }, ...first] });
    });

    await waitFor(() => expect(result.current.lastAlertEvent?.id).toBe(2));
  });

  it('does not alert when the filter changes and brings a different result set', async () => {
    // انحدار: تغيير الفلتر كان يجعل أحداثاً قديمة تبدو جديدة فتُطلق إنذاراً كاذباً
    const first = [{ id: 1, severity: 'critical', category: 'military', title: 'a' }];
    const { result, rerender } = renderHook(
      ({ ev, f }) => useAudioAlert(ev, f),
      { initialProps: { ev: first, f: { category: '' } } }
    );

    act(() => {
      rerender({
        ev: [{ id: 99, severity: 'critical', category: 'nuclear', title: 'old-but-newly-visible' }],
        f: { category: 'nuclear' },
      });
    });

    await waitFor(() => expect(result.current.recentAlerts).toHaveLength(0));
    expect(result.current.lastAlertEvent).toBeNull();
  });
});
