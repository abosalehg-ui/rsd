/**
 * رصد - شريط حالة البيانات فوق محتوى معروض من استطلاع (`usePolling`).
 *
 * يظهر حين يفشل التحديث والبيانات القديمة ما زالت معروضة: لولاه لبقي رقم فترة
 * سابقة تحت عنوان الفترة المختارة بلا أي إشارة. `stale` يميّز «فشل طلب الفترة
 * الجديدة» (المعروض لفترة أخرى) عن «فشل تحديث دوري» (المعروض للفترة نفسها).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

export default function StaleNotice({ error, stale = false, onRetry, className = '' }) {
  const { t } = useTranslation();
  if (!error) return null;
  return (
    <p
      role="alert"
      className={`flex items-start gap-1.5 rounded border border-red-500/30 bg-red-500/10 px-2.5 py-1.5 text-xs text-red-200 ${className}`}
    >
      <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" aria-hidden="true" />
      <span className="flex-1">{stale ? t('common.staleFailed') : t('common.refreshFailed')}</span>
      {onRetry && (
        <button onClick={() => onRetry()} className="shrink-0 underline focus-ring rounded">{t('common.retry')}</button>
      )}
    </p>
  );
}

/** صنف التعتيم للمحتوى أثناء جلب فترة جديدة أو بعد فشلها. */
export const staleClass = (stale) => (stale ? 'opacity-60 transition-opacity' : 'transition-opacity');
