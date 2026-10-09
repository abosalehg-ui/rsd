import { describe, it, expect } from 'vitest';
import ar from './locales/ar.json';
import en from './locales/en.json';
import i18n from './index';

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

describe('plurals', () => {
  const tr = (lng, key, count) => i18n.getFixedT(lng)(key, { count });

  it('uses the six Arabic plural forms', () => {
    expect([0, 1, 2, 3, 11, 100].map(n => tr('ar', 'replay.count', n)))
      .toEqual(['لا أحداث', '1 حدث', 'حدثان', '3 أحداث', '11 حدثًا', '100 حدث']);
    expect([0, 1, 2, 3, 11, 100].map(n => tr('ar', 'impact.sectorStories', n)))
      .toEqual(['لا قصص', '1 قصة', 'قصتان', '3 قصص', '11 قصة', '100 قصة']);
    expect([1, 2, 5, 25].map(n => tr('ar', 'news.countTitle', n)))
      .toEqual(['1 حدث في الفترة', 'حدثان في الفترة', '5 أحداث في الفترة', '25 حدثًا في الفترة']);
  });

  it('uses singular and plural in English', () => {
    expect(tr('en', 'replay.count', 1)).toBe('1 event');
    expect(tr('en', 'replay.count', 3)).toBe('3 events');
    expect(tr('en', 'impact.sectorStories', 1)).toBe('1 story');
    expect(tr('en', 'news.countTitle', 2)).toBe('2 events in this period');
  });

  it('defines every Arabic form for each counted key', () => {
    const forms = ['zero', 'one', 'two', 'few', 'many', 'other'];
    [['replay', 'count'], ['impact', 'sectorStories'], ['news', 'countTitle']].forEach(([ns, key]) => {
      forms.forEach(f => expect(ar[ns][`${key}_${f}`], `${ns}.${key}_${f}`).toBeTruthy());
      ['one', 'other'].forEach(f => expect(en[ns][`${key}_${f}`], `${ns}.${key}_${f}`).toBeTruthy());
    });
  });
});
