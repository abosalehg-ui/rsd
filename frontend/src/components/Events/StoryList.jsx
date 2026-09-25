/**
 * رصد - قائمة قصص مجمّعة زمنيًا (آخر ساعة / اليوم / أمس / أقدم) برؤوس لاصقة.
 * الترتيب داخل كل مجموعة كما يأتي من الخادم (الأحدث أولًا).
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import EventCard from './EventCard';

export function timeGroup(dateStr, now = new Date()) {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return 'older';
  if (now - d < 3600 * 1000) return 'hour';
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (d >= startOfToday) return 'today';
  const startOfYesterday = new Date(startOfToday.getTime() - 86400 * 1000);
  if (d >= startOfYesterday) return 'yesterday';
  return 'older';
}

const ORDER = ['hour', 'today', 'yesterday', 'older'];

export default function StoryList({ events = [], activeId = null, onOpen }) {
  const { t } = useTranslation();
  const groups = useMemo(() => {
    const now = new Date();
    const map = new Map(ORDER.map(k => [k, []]));
    events.forEach(ev => map.get(timeGroup(ev.event_date, now)).push(ev));
    return ORDER.map(k => [k, map.get(k)]).filter(([, items]) => items.length);
  }, [events]);

  return groups.map(([key, items]) => (
    <section key={key} aria-label={t(`events.groups.${key}`)}>
      <h3 className="sticky top-0 z-10 flex items-center gap-2 bg-rasad-panel/95 backdrop-blur px-4 py-1.5 text-xs font-semibold text-slate-300 border-b border-rasad-border">
        {t(`events.groups.${key}`)}
        <span className="font-mono font-normal text-slate-500">{items.length}</span>
      </h3>
      {items.map(ev => (
        <EventCard key={ev.id} event={ev} active={ev.id === activeId} onOpen={onOpen} />
      ))}
    </section>
  ));
}
