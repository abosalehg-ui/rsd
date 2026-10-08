import { describe, it, expect } from 'vitest';
import { SEVERITIES } from './constants';
import {
  LOW_CONFIDENCE, confidenceColor, confidenceFormula, confidenceLevel, entityName, pct, relationText,
} from './chains';

describe('chains helpers', () => {
  it.each([[0.9, 'high'], [0.7, 'high'], [0.69, 'medium'], [LOW_CONFIDENCE, 'medium'], [0.54, 'low'], [null, 'low']])(
    'confidenceLevel(%s) = %s', (v, level) => expect(confidenceLevel(v)).toBe(level),
  );

  it('colours confidence from the severity scale (no hand-written hex)', () => {
    expect(confidenceColor(0.8)).toBe(SEVERITIES.low.color);
    expect(confidenceColor(0.6)).toBe(SEVERITIES.medium.color);
    expect(confidenceColor(0.4)).toBe(SEVERITIES.high.color);
  });

  it('formats percentages and formulas', () => {
    expect(pct(0.456)).toBe('46%');
    expect(pct(undefined)).toBe('0%');
    expect(confidenceFormula({
      confidence: 0.68, evidence: { components: { template: 0.8, entity: 0.95, time: 1, source_trust: 0.9 } },
    })).toBe('0.68 = 0.8 × 0.95 × 1 × 0.9');
    expect(confidenceFormula({})).toBe('');
  });

  it('picks the language', () => {
    const link = { relation_ar: 'ضربة ← رد', relation_en: 'Strike → retaliation' };
    expect(relationText(link, 'ar')).toBe('ضربة ← رد');
    expect(relationText(link, 'en')).toBe('Strike → retaliation');
    expect(entityName({ key: 'IR', ar: 'إيران', en: 'Iran' }, 'ar')).toBe('إيران');
    expect(entityName({ key: 'x' }, 'en')).toBe('x');
  });
});
