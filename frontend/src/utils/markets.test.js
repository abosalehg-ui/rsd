import { describe, it, expect } from 'vitest';
import { daysSince, direction, formatObservedDate, formatPct, formatQuote } from './markets';

describe('markets formatting', () => {
  it('formats quotes and missing values', () => {
    expect(formatQuote(84.271)).toBe('84.27');
    expect(formatQuote(null)).toBe('—');
    expect(formatQuote('x')).toBe('—');
  });

  it('always signs the percentage change', () => {
    expect(formatPct(5)).toBe('+5.00%');
    expect(formatPct(-1.2)).toBe('−1.20%');
    expect(formatPct(0)).toBe('0.00%');
    expect(formatPct(null)).toBe('—');
  });

  it.each([[1.5, 'up'], [-0.3, 'down'], [0, 'flat'], [0.001, 'flat'], [null, 'flat']])('direction(%s) = %s', (v, d) => {
    expect(direction(v)).toBe(d);
  });

  it('reads FRED dates as UTC days (no off-by-one in western time zones)', () => {
    expect(formatObservedDate('2026-10-05', 'en')).toBe('5 Oct 2026');
    expect(formatObservedDate('2026-10-05', 'ar')).toMatch(/5/);
    expect(formatObservedDate(null, 'en')).toBe('—');
    expect(formatObservedDate('garbage', 'en')).toBe('—');
  });

  it('counts whole UTC days since the observation', () => {
    const now = new Date('2026-10-08T03:00:00Z');
    expect(daysSince('2026-10-05', now)).toBe(3);
    expect(daysSince('2026-10-08', now)).toBe(0);
    expect(daysSince(null, now)).toBeNull();
  });
});
