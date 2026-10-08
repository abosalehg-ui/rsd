/**
 * رصد - إعادة التشغيل الزمني للخريطة والكرة.
 *
 * منطق نقي (قابل للاختبار بلا DOM): النافذة تُقسَّم ساعات، والإطار رقم `step`
 * يعرض كل حدث وقع بين بداية النافذة ونهاية تلك الساعة — فتتراكم الأحداث على
 * الخريطة ساعة بساعة كما وقعت. الأحداث بلا تاريخ صالح لا تظهر في الإعادة.
 */

export const REPLAY_WINDOWS = [48, 72];
export const HOUR_MS = 3600 * 1000;

/** بداية النافذة: آخر `hours` ساعة كاملة قبل `now` (تُقرَّب لبداية الساعة). */
export function replayStart(now, hours) {
  const end = new Date(now);
  end.setMinutes(0, 0, 0);
  return new Date(end.getTime() - (hours - 1) * HOUR_MS);
}

/** نهاية الإطار `step` (0 … hours-1): نهاية الساعة رقم step من بداية النافذة. */
export function frameEnd(start, step) {
  return new Date(new Date(start).getTime() + (step + 1) * HOUR_MS);
}

const eventTime = (ev) => {
  const t = Date.parse(ev?.event_date);
  return Number.isFinite(t) ? t : null;
};

/** الأحداث المتراكمة حتى نهاية الإطار `step`. */
export function eventsUntil(events, start, step) {
  const from = new Date(start).getTime();
  const to = frameEnd(start, step).getTime();
  return (events || []).filter(ev => {
    const t = eventTime(ev);
    return t !== null && t >= from && t < to;
  });
}

/** عدد الأحداث الجديدة في كل ساعة من النافذة — لرسم شريط الكثافة تحت المنزلق. */
export function hourlyCounts(events, start, hours) {
  const from = new Date(start).getTime();
  const counts = new Array(hours).fill(0);
  (events || []).forEach(ev => {
    const t = eventTime(ev);
    if (t === null) return;
    const idx = Math.floor((t - from) / HOUR_MS);
    if (idx >= 0 && idx < hours) counts[idx] += 1;
  });
  return counts;
}
