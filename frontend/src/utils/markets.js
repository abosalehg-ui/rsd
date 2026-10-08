/**
 * رصد - تنسيق قيم الطاقة والأسواق.
 *
 * قيم FRED يومية بتاريخ يوم التداول (`YYYY-MM-DD`) لا لحظة — تُقرأ تاريخًا
 * بتوقيت UTC كي لا يزيحها فرق المنطقة الزمنية يومًا للخلف.
 */

/** «84.27» — رقمان عشريان وأرقام لاتينية في اللغتين كبقية العدّادات. */
export function formatQuote(value) {
  if (value == null || !Number.isFinite(Number(value))) return '—';
  return Number(value).toFixed(2);
}

/** «+5.00%» / «−1.20%» — الإشارة صريحة دائمًا. */
export function formatPct(pct) {
  if (pct == null || !Number.isFinite(Number(pct))) return '—';
  const v = Number(pct);
  const sign = v > 0 ? '+' : v < 0 ? '−' : '';
  return `${sign}${Math.abs(v).toFixed(2)}%`;
}

/** اتجاه التغيّر: up | down | flat (أقل من 0.005% = ثابت). */
export function direction(pct) {
  const v = Number(pct);
  if (!Number.isFinite(v) || Math.abs(v) < 0.005) return 'flat';
  return v > 0 ? 'up' : 'down';
}

const localeFor = (lang) => (lang === 'ar' ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB');

/** تاريخ ملاحظة FRED بلغة الواجهة: «5 أكتوبر 2026». */
export function formatObservedDate(iso, lang, opts = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!iso) return '—';
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(localeFor(lang), { ...opts, timeZone: 'UTC' });
}

/** كم يومًا مضى على تاريخ الملاحظة (بأيام UTC كاملة). */
export function daysSince(iso, now = new Date()) {
  if (!iso) return null;
  const d = Date.parse(`${String(iso).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d)) return null;
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Math.max(0, Math.round((today - d) / 86400000));
}

export const CHANGE_CLASS = {
  up: 'text-emerald-300',
  down: 'text-red-300',
  flat: 'text-slate-400',
};
