/**
 * رصد - خطاف الطبقات المنبثقة (نوافذ، أدراج، قوائم).
 *
 * مكدّس واحد على مستوى الوحدة ومستمع `keydown` واحد على المستند: Escape يغلق
 * الطبقة العليا وحدها. لو سجّلت كل طبقة مستمعها لأغلقت ضغطة واحدة الدرج
 * والنافذة فوقه معًا.
 *
 * - `trap`: يحبس Tab داخل الحاوية (النوافذ `aria-modal`). الأدراج غير الحاجبة
 *   والقوائم تتركه false فيبقى بقية الصفحة في متناول لوحة المفاتيح.
 * - التركيز الأولي على `initialFocusRef` (أو الحاوية)، ويُعاد عند الإغلاق إلى
 *   ما كان مركّزًا قبل الفتح إن بقي في الصفحة.
 * - `onClose` في مرجع: المستدعي يمرّر دالة جديدة في كل رسم، وربط التأثير بها
 *   يعيد التركيز إلى ما قبل الطبقة مع كل تحديث دوري للتطبيق.
 */
import { useEffect, useRef } from 'react';

const FOCUSABLE = [
  'a[href]', 'area[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])', 'textarea:not([disabled])', 'iframe', 'summary',
  '[contenteditable="true"]', '[tabindex]:not([tabindex="-1"])',
].join(',');

const stack = [];

function focusables(container) {
  return [...container.querySelectorAll(FOCUSABLE)].filter(el => !el.closest('[hidden], [inert]'));
}

function onKeyDown(e) {
  const top = stack[stack.length - 1];
  if (!top) return;
  if (e.key === 'Escape') {
    // الطبقة العليا وحدها؛ ولا يصل الحدث لمستمعين أبعد (مثل Leaflet)
    e.stopPropagation();
    top.onCloseRef.current?.();
    return;
  }
  if (e.key !== 'Tab' || !top.trap) return;
  const container = top.containerRef.current;
  if (!container) return;
  const items = focusables(container);
  if (!items.length) {
    e.preventDefault();
    container.focus?.();
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement;
  if (!container.contains(active)) {
    e.preventDefault();
    (e.shiftKey ? last : first).focus();
  } else if (e.shiftKey && (active === first || active === container)) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && active === last) {
    e.preventDefault();
    first.focus();
  }
}

/** عدد الطبقات المفتوحة — للاختبارات والتشخيص. */
export const modalDepth = () => stack.length;

export function useModal(open, onClose, { containerRef, initialFocusRef, trap = true, autoFocus = true } = {}) {
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);

  const fallbackRef = useRef(null);
  const ref = containerRef || fallbackRef;

  useEffect(() => {
    if (!open) return undefined;
    const entry = { onCloseRef, containerRef: ref, trap };
    const prev = document.activeElement;
    stack.push(entry);
    if (stack.length === 1) document.addEventListener('keydown', onKeyDown);
    if (autoFocus) (initialFocusRef?.current || ref.current)?.focus?.();

    return () => {
      const i = stack.indexOf(entry);
      if (i !== -1) stack.splice(i, 1);
      if (!stack.length) document.removeEventListener('keydown', onKeyDown);
      // العنصر السابق قد يكون أُزيل (زر داخل درج أُغلق): لا نركّز عنصرًا منفصلًا
      if (autoFocus && prev instanceof HTMLElement && prev.isConnected) prev.focus();
    };
    // المراجع ثابتة الهوية؛ trap وautoFocus إعدادات لا تتغيّر أثناء الفتح
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return ref;
}
