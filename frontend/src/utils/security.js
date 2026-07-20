/**
 * رصد - أدوات أمنية مشتركة
 *
 * بيانات الأحداث/الضربات/الطيران/الخلاصات تأتي من مصادر خارجية (RSS/OSINT/ADS-B)
 * وقد تحتوي محتوى خبيثاً. هذه الأدوات تُستخدم في كل موضع يعرض بيانات خارجية:
 *   - esc()      قبل أي حقن في innerHTML (نوافذ Leaflet / تسميات globe.gl).
 *   - safeUrl()  قبل أي href لمنع javascript:/data: وأشباهها.
 */

const ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** تهريب HTML — يمنع حقن الوسوم والسكربتات عند الإدراج في innerHTML. */
export const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ESC_MAP[c]);

/**
 * يسمح فقط بروابط http/https المطلقة — يمنع javascript:، data:، file: وأشباهها.
 * يعيد سلسلة فارغة للروابط غير الآمنة (فيُخفى الرابط بدل عرضه).
 */
export const safeUrl = (u) => {
  const s = String(u ?? '').trim();
  return /^https?:\/\//i.test(s) ? s : '';
};
