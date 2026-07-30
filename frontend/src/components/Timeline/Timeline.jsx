/**
 * رصد - الخط الزمني التفاعلي
 *
 * النافذة الزمنية مرفوعة إلى App وموصولة بـ filters.hours: كانت محلية هنا
 * فتُظهر أزرار 48س بلا أثر، لأن الأحداث المجلوبة محدودة أصلاً بـ filters.hours.
 */
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CATEGORIES, TIME_WINDOWS, categoryOf, severityOf } from '../../utils/constants';
import { Clock, Calendar } from 'lucide-react';

export default function Timeline({ events = [], loading = false, hours = 24, onHoursChange, onSelectEvent }) {
  const { t, i18n } = useTranslation();
  const [selectedCategory, setSelectedCategory] = useState('');

  const sorted = useMemo(() => {
    const list = [...events].sort((a, b) => new Date(b.event_date) - new Date(a.event_date));
    return selectedCategory ? list.filter(e => e.category === selectedCategory) : list;
  }, [events, selectedCategory]);

  // تجميع حسب الساعة — مفتاح ISO قابل للفرز، والعرض بلغة الواجهة
  const grouped = useMemo(() => {
    const groups = new Map();
    sorted.forEach(ev => {
      const d = new Date(ev.event_date);
      if (Number.isNaN(d.getTime())) return;
      const key = new Date(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()).toISOString();
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(ev);
    });
    return [...groups.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [sorted]);

  const hourFormatter = useMemo(
    // تقويم ميلادي وأرقام لاتينية (ar-SA وحده هجري/هندي)
    () => new Intl.DateTimeFormat(i18n.language === 'ar' ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
    }),
    [i18n.language]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-rasad-border gap-2">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-300" aria-hidden="true" />
          <span className="text-sm font-bold">{t('timeline.title')}</span>
        </div>
        <div className="flex items-center gap-1 flex-wrap justify-end" role="group" aria-label={t('timeline.window')}>
          {TIME_WINDOWS.map(h => (
            <button key={h} onClick={() => onHoursChange?.(h)}
              aria-pressed={hours === h}
              className={`text-[11px] px-1.5 py-1 rounded focus-ring ${hours === h ? 'bg-cyan-400/20 text-cyan-200' : 'text-slate-300 hover:text-white'}`}>
              {t('time.hoursShort', { count: h })}
            </button>
          ))}
        </div>
      </div>

      {/* فلتر التصنيف */}
      <div className="flex gap-1 px-3 py-1.5 border-b border-rasad-border/50 overflow-x-auto">
        <button onClick={() => setSelectedCategory('')}
          aria-pressed={!selectedCategory}
          className={`text-[11px] px-2 py-1 rounded whitespace-nowrap focus-ring ${!selectedCategory ? 'bg-cyan-400/20 text-cyan-200' : 'text-slate-300'}`}>
          {t('timeline.all')}
        </button>
        {Object.entries(CATEGORIES).map(([k, c]) => (
          <button key={k} onClick={() => setSelectedCategory(selectedCategory === k ? '' : k)}
            aria-pressed={selectedCategory === k}
            aria-label={t(`categories.${k}`)}
            title={t(`categories.${k}`)}
            className={`text-[11px] px-2 py-1 rounded whitespace-nowrap focus-ring ${selectedCategory === k ? 'text-white' : 'text-slate-300'}`}
            style={selectedCategory === k ? { background: c.color + '20', color: c.color } : {}}>
            <span aria-hidden="true">{c.icon}</span>
          </button>
        ))}
      </div>

      {/* المحتوى */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {loading && grouped.length === 0 ? (
          <div className="space-y-2" aria-busy="true" aria-label={t('common.loading')}>
            {[0, 1, 2, 3].map(i => <div key={i} className="shimmer h-14 rounded-lg" />)}
          </div>
        ) : grouped.length === 0 ? (
          <div className="text-center text-slate-300 text-sm mt-8">{t('timeline.noEvents')}</div>
        ) : (
          grouped.map(([timeKey, items]) => (
            <div key={timeKey} className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-3 h-3 text-slate-400" aria-hidden="true" />
                <span className="text-[11px] font-mono text-slate-300">{hourFormatter.format(new Date(timeKey))}</span>
                <span className="text-[11px] bg-rasad-border text-slate-300 px-1.5 rounded">{items.length}</span>
                <div className="flex-1 h-px bg-rasad-border" />
              </div>
              <div className="space-y-1 ms-4 border-s border-rasad-border ps-3">
                {items.map(ev => {
                  const cat = categoryOf(ev.category);
                  const sev = severityOf(ev.severity);
                  return (
                    <div key={ev.id}
                      role="button"
                      tabIndex={0}
                      className="relative flex items-start gap-2 py-1 cursor-pointer hover:bg-rasad-border/20 rounded px-1 -ms-1 focus-ring"
                      onClick={() => onSelectEvent?.(ev)}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectEvent?.(ev); } }}>
                      <div className="absolute -start-[19px] top-2 w-2 h-2 rounded-full border-2 border-rasad-panel"
                        style={{ background: cat.color }} aria-hidden="true" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1 mb-0.5">
                          <span className="text-[11px]" aria-hidden="true">{cat.icon}</span>
                          <span className="text-[11px] px-1 rounded" style={{ background: sev.color + '20', color: sev.color }}>
                            {t(`severity.${ev.severity}`, { defaultValue: t('severity.low') })}
                          </span>
                        </div>
                        <p className="text-xs text-slate-200 leading-relaxed line-clamp-2">{ev.title}</p>
                        <span className="text-[11px] text-slate-300">
                          {t(`countries.${ev.country_code}`, { defaultValue: ev.country || '' })} • <bdi>{ev.source}</bdi>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
