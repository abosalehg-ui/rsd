/**
 * رصد - رسالة نتيجة التحديث اليدوي من رد `POST /api/refresh`: الخادم يعيد 200 حتى حين
 * يفشل كل جامع، فالحكم من `sources` لا من حالة HTTP — وإلا قيل «تم التحديث»
 * فوق بيانات لم تتغيّر.
 */
export function refreshToast(result, t) {
  const sources = Object.values(result?.sources || {});
  const failed = sources.filter(s => s?.status === 'error').length;
  if (sources.length && failed === sources.length) return { kind: 'error', text: t('app.refreshAllFailed') };
  if (failed) return { kind: 'error', text: t('app.refreshPartial', { failed, total: sources.length }) };
  return { kind: 'ok', text: t('app.refreshDone') };
}
