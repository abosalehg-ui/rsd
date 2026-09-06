/**
 * اختبارات حالة الفلاتر في عنوان الصفحة.
 *
 * السيناريو الذي تحرسه: المستخدم يضبط "عسكري + إيران + 72 ساعة" ثم يُعيد
 * التحميل أو يشارك الرابط. كانت الحالة محليّة بالكامل فتضيع في الحالتين.
 * وتحرس أيضاً أن عنواناً يكتبه المستخدم بيده لا يُنتج قيمة يرفضها الخادم بـ422.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useFilters } from './usePolling';

function setUrl(search) {
  window.history.replaceState({}, '', search ? `/?${search}` : '/');
}

describe('useFilters', () => {
  beforeEach(() => setUrl(''));

  it('يبدأ بالقيم الافتراضية حين لا يحمل العنوان شيئاً', () => {
    const { result } = renderHook(() => useFilters());
    expect(result.current.filters).toMatchObject({
      category: '', severity: '', country_code: '', source: '', search: '', hours: 24,
    });
  });

  it('يقرأ الفلاتر من عنوان الصفحة عند التركيب', () => {
    setUrl('category=military&country_code=IR&hours=72');
    const { result } = renderHook(() => useFilters());
    expect(result.current.filters.category).toBe('military');
    expect(result.current.filters.country_code).toBe('IR');
    expect(result.current.filters.hours).toBe(72);
  });

  it('يكتب الفلاتر في العنوان عند تغييرها', () => {
    const { result } = renderHook(() => useFilters());
    act(() => result.current.updateFilter('category', 'nuclear'));

    const params = new URLSearchParams(window.location.search);
    expect(params.get('category')).toBe('nuclear');
  });

  it('لا يُبقي القيم الافتراضية في العنوان (يبقى نظيفاً)', () => {
    setUrl('category=military');
    const { result } = renderHook(() => useFilters());
    act(() => result.current.updateFilter('category', ''));

    expect(new URLSearchParams(window.location.search).has('category')).toBe(false);
  });

  it('يُعيد الضبط فيُفرِغ العنوان', () => {
    setUrl('category=military&severity=high&hours=168');
    const { result } = renderHook(() => useFilters());
    act(() => result.current.resetFilters());

    expect(window.location.search).toBe('');
    expect(result.current.filters.hours).toBe(24);
  });

  it('يرفض نافذة زمنية خارج القائمة المدعومة', () => {
    // الخادم يقبل 1..720 فقط؛ 99999 كانت ستعيد 422 وتُفرغ اللوحة
    setUrl('hours=99999');
    const { result } = renderHook(() => useFilters());
    expect(result.current.filters.hours).toBe(24);
  });

  it('يقتطع نص البحث إلى حدّ الخادم', () => {
    setUrl(`search=${'ا'.repeat(400)}`);
    const { result } = renderHook(() => useFilters());
    expect(result.current.filters.search.length).toBe(100);
  });
});
