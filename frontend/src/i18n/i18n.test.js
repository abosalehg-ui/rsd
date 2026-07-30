import { describe, it, expect } from 'vitest';
import ar from './locales/ar.json';
import en from './locales/en.json';

// يجمع كل المفاتيح الورقية (leaf keys) بمسارها المنقّط
function leafKeys(obj, prefix = '') {
  const keys = [];
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) keys.push(...leafKeys(v, path));
    else keys.push(path);
  }
  return keys.sort();
}

// نُزيل لواحق الجمع في CLDR — للعربية فئات أكثر (_two/_few/_many) من الإنجليزية،
// وهو اختلاف مشروع لا نقص ترجمة. نقارن المفاتيح الأساسية.
const stripPlural = (k) => k.replace(/_(zero|one|two|few|many|other)$/, '');
const baseKeySet = (obj) => [...new Set(leafKeys(obj).map(stripPlural))].sort();

describe('i18n locale parity', () => {
  it('ar and en expose the same base key set', () => {
    const arKeys = baseKeySet(ar);
    const enKeys = baseKeySet(en);
    const onlyAr = arKeys.filter(k => !enKeys.includes(k));
    const onlyEn = enKeys.filter(k => !arKeys.includes(k));
    expect(onlyAr, `مفاتيح في ar بلا مقابل en: ${onlyAr}`).toEqual([]);
    expect(onlyEn, `مفاتيح في en بلا مقابل ar: ${onlyEn}`).toEqual([]);
  });

  it('common.loading exists in both', () => {
    expect(ar.common.loading).toBeTruthy();
    expect(en.common.loading).toBeTruthy();
  });
});
