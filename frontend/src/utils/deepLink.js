/**
 * رصد - رابط مشاركة لكل حدث: `?event=ID`.
 *
 * يُقرأ عند التحميل فيفتح لوحة التفاصيل مباشرة، ويُكتب بـ replaceState كلما
 * فُتح حدث أو أُغلق — مع إبقاء بقية المعاملات (الفلاتر في `useFilters`) كما هي.
 */

export const EVENT_PARAM = 'event';

/** معرّف الحدث من العنوان، أو null إن غاب أو لم يكن عددًا صحيحًا موجبًا. */
export function readEventId(search = typeof window !== 'undefined' ? window.location.search : '') {
  try {
    const raw = new URLSearchParams(search).get(EVENT_PARAM);
    if (!raw || !/^\d{1,12}$/.test(raw)) return null;
    const id = Number(raw);
    return id > 0 ? id : null;
  } catch {
    return null;
  }
}

/** رابط كامل يفتح الحدث — بلا فلاتر العرض الحالية كي يراه المستلم كما هو. */
export function eventLink(id, location = typeof window !== 'undefined' ? window.location : null) {
  if (!location) return `?${EVENT_PARAM}=${id}`;
  const url = new URL(location.pathname, location.origin);
  url.searchParams.set(EVENT_PARAM, String(id));
  return url.toString();
}

/** يضع معرّف الحدث في العنوان (أو يزيله عند null) دون إضافة خطوة للتاريخ. */
export function writeEventId(id) {
  if (typeof window === 'undefined' || !window.history?.replaceState) return;
  try {
    const params = new URLSearchParams(window.location.search);
    if (id == null || typeof id !== 'number') params.delete(EVENT_PARAM);
    else params.set(EVENT_PARAM, String(id));
    const query = params.toString();
    window.history.replaceState(null, '', query
      ? `${window.location.pathname}?${query}`
      : window.location.pathname);
  } catch { /* العنوان اختياري — التفاصيل تعمل بدونه */ }
}

/** نسخ إلى الحافظة مع بديل `execCommand` للمتصفحات/السياقات بلا Clipboard API. */
export async function copyText(text) {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch { /* نقع على البديل */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand?.('copy') ?? false;
    ta.remove();
    return Boolean(ok);
  } catch {
    return false;
  }
}
