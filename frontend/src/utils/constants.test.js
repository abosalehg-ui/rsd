import { describe, it, expect } from 'vitest';
import { CATEGORIES, SEVERITIES, COUNTRIES, timeAgo, formatNumber } from './constants';

describe('constants', () => {
  it('exposes all expected categories with shape', () => {
    for (const key of ['military', 'diplomatic', 'humanitarian', 'nuclear', 'economic', 'general']) {
      expect(CATEGORIES[key]).toBeDefined();
      expect(CATEGORIES[key].label).toBeTruthy();
      expect(CATEGORIES[key].color).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  it('orders severities from critical to low', () => {
    expect(Object.keys(SEVERITIES)).toEqual(['critical', 'high', 'medium', 'low']);
  });

  it('flags every country', () => {
    for (const code of Object.keys(COUNTRIES)) {
      expect(COUNTRIES[code].flag).toBeTruthy();
      expect(COUNTRIES[code].name).toBeTruthy();
    }
  });
});

describe('timeAgo', () => {
  it('returns "الآن" for < 60s', () => {
    const t = new Date(Date.now() - 5 * 1000).toISOString();
    expect(timeAgo(t)).toBe('الآن');
  });
  it('returns minutes for < 1h', () => {
    const t = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(timeAgo(t)).toMatch(/منذ 5 دقيقة/);
  });
  it('returns hours for < 1d', () => {
    const t = new Date(Date.now() - 3 * 3600 * 1000).toISOString();
    expect(timeAgo(t)).toMatch(/منذ 3 ساعة/);
  });
  it('returns days for older', () => {
    const t = new Date(Date.now() - 2 * 86400 * 1000).toISOString();
    expect(timeAgo(t)).toMatch(/منذ 2 يوم/);
  });
});

describe('formatNumber', () => {
  it('< 1000 → as-is', () => {
    expect(formatNumber(42)).toBe('42');
  });
  it('1000+ → K', () => {
    expect(formatNumber(1500)).toBe('1.5K');
  });
  it('1000000+ → M', () => {
    expect(formatNumber(2_300_000)).toBe('2.3M');
  });
});
