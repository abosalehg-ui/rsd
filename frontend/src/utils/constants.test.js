import { describe, it, expect, vi } from 'vitest';
import {
  CATEGORIES, SEVERITIES, COUNTRIES, CONFIDENCE, IRAN_EVENT_TYPES,
  SOURCES, TIME_WINDOWS, categoryOf, severityOf, timeAgo, formatNumber,
  escalationColor, scoreColor,
} from './constants';

// بديل بسيط لدالة الترجمة: يعيد المفتاح + العدد كي نتحقّق من اختيار المفتاح
const t = vi.fn((key, opts) => (opts?.count !== undefined ? `${key}:${opts.count}` : key));

describe('constants', () => {
  it('exposes all expected categories with a color and icon (no hardcoded labels)', () => {
    for (const key of ['military', 'diplomatic', 'humanitarian', 'nuclear', 'economic', 'general']) {
      expect(CATEGORIES[key]).toBeDefined();
      expect(CATEGORIES[key].color).toMatch(/^#[0-9a-f]{6}$/i);
      expect(CATEGORIES[key].icon).toBeTruthy();
      // التسميات انتقلت إلى i18n — يجب ألا تبقى هنا
      expect(CATEGORIES[key].label).toBeUndefined();
    }
  });

  it('orders severities from critical to low', () => {
    expect(Object.keys(SEVERITIES)).toEqual(['critical', 'high', 'medium', 'low']);
  });

  it('flags every country and keeps names out of the module', () => {
    for (const code of Object.keys(COUNTRIES)) {
      expect(COUNTRIES[code].flag).toBeTruthy();
      expect(COUNTRIES[code].name).toBeUndefined();
    }
  });

  it('exposes confidence levels and Iran event types without labels', () => {
    for (const level of ['HIGH', 'MEDIUM', 'LOW']) {
      expect(CONFIDENCE[level].color).toMatch(/^#[0-9a-f]{6}$/i);
      expect(CONFIDENCE[level].label).toBeUndefined();
    }
    for (const type of ['strike', 'launch', 'movement', 'nuclear', 'diplomatic']) {
      expect(IRAN_EVENT_TYPES[type].icon).toBeTruthy();
      expect(IRAN_EVENT_TYPES[type].label).toBeUndefined();
    }
  });

  it('lists the backend source ids and shared time windows', () => {
    expect(SOURCES).toContain('gdelt');
    expect(SOURCES).toContain('iran_osint');
    expect(TIME_WINDOWS[0]).toBeLessThan(TIME_WINDOWS[TIME_WINDOWS.length - 1]);
  });
});

describe('categoryOf / severityOf', () => {
  it('returns the matching entry', () => {
    expect(categoryOf('military')).toBe(CATEGORIES.military);
    expect(severityOf('critical')).toBe(SEVERITIES.critical);
  });

  it('falls back for unknown or missing values', () => {
    expect(categoryOf('does-not-exist')).toBe(CATEGORIES.general);
    expect(categoryOf(undefined)).toBe(CATEGORIES.general);
    expect(severityOf('nope')).toBe(SEVERITIES.low);
  });
});

describe('timeAgo', () => {
  it('uses the "now" key for < 60s', () => {
    expect(timeAgo(new Date(Date.now() - 5 * 1000).toISOString(), t)).toBe('time.now');
  });
  it('uses minutes for < 1h', () => {
    expect(timeAgo(new Date(Date.now() - 5 * 60 * 1000).toISOString(), t)).toBe('time.minutes:5');
  });
  it('uses hours for < 1d', () => {
    expect(timeAgo(new Date(Date.now() - 3 * 3600 * 1000).toISOString(), t)).toBe('time.hours:3');
  });
  it('uses days for older', () => {
    expect(timeAgo(new Date(Date.now() - 2 * 86400 * 1000).toISOString(), t)).toBe('time.days:2');
  });
  it('returns an empty string for an invalid date instead of NaN text', () => {
    expect(timeAgo('not-a-date', t)).toBe('');
    expect(timeAgo(undefined, t)).toBe('');
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

describe('score color helpers', () => {
  it('escalationColor thresholds (30/15)', () => {
    expect(escalationColor(40)).toBe(escalationColor(31)); // فوق 30 = أحمر
    expect(escalationColor(20)).not.toBe(escalationColor(40)); // متوسط ≠ عالٍ
    expect(escalationColor(5)).not.toBe(escalationColor(20)); // منخفض ≠ متوسط
    expect(escalationColor(0)).toBe(escalationColor(null)); // يعامل null كصفر
  });
  it('scoreColor four tiers (75/50/25)', () => {
    const tiers = [scoreColor(80), scoreColor(60), scoreColor(30), scoreColor(10)];
    expect(new Set(tiers).size).toBe(4); // أربع مراتب متمايزة
  });
});
