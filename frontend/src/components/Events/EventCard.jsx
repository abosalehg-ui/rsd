/**
 * رصد - بطاقة خبر/قصة، مشتركة بين قائمة الأحداث والرصد النووي.
 *
 * التسلسل البصري: شريط جانبي بلون الخطورة (يُرى قبل القراءة) ← سطر وصفي
 * صغير (التصنيف أو الموضوع، عدد المصادر، الوقت) ← العنوان بخط أكبر ← المكان
 * والمصدر، ودرجة الخطر للأخبار النووية. الموقع التقريبي (مستوى الدولة)
 * يُعلَّم بدبوس متقطّع كي لا يُفهم كموقع دقيق.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { MapPin, CircleDashed, Layers } from 'lucide-react';
import { COUNTRIES, categoryOf, riskColor, severityOf, timeAgo } from '../../utils/constants';
import { Icon } from '../../utils/icons';

export function RiskPill({ score, className = '' }) {
  const { t } = useTranslation();
  if (score === null || score === undefined) return null;
  const color = riskColor(score);
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-xs font-semibold tabular-nums ${className}`}
      style={{ color, background: `${color}1f`, boxShadow: `inset 0 0 0 1px ${color}55` }}
      title={t('risk.score')}
    >
      {Math.round(score)}
    </span>
  );
}

export function placeLabel(ev, t) {
  const country = ev.country_code
    ? t(`countries.${ev.country_code}`, { defaultValue: ev.country || ev.country_code })
    : (ev.country || '');
  const place = ev.extra?.place_name;
  if (place && place !== country) return country ? `${country} · ${place}` : place;
  return country;
}

export default function EventCard({ event, onOpen, active = false }) {
  const { t } = useTranslation();
  const cat = categoryOf(event.category);
  const sev = severityOf(event.severity);
  const flag = COUNTRIES[event.country_code]?.flag || '';
  const approx = event.geo_precision === 'country';
  const place = placeLabel(event, t);
  const kicker = event.topic
    ? t(`topics.${event.topic}`, { defaultValue: t(`categories.${event.category}`) })
    : t(`categories.${event.category}`, { defaultValue: t('categories.general') });
  const sourceCount = event.story_source_count || 1;

  const open = () => onOpen?.(event);

  return (
    <article
      role="button"
      tabIndex={0}
      aria-current={active || undefined}
      onClick={open}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } }}
      className={`relative border-b border-rasad-border/60 ps-4 pe-3 py-3 cursor-pointer transition-colors focus-ring
        hover:bg-rasad-raised ${active ? 'bg-rasad-raised' : ''}`}
    >
      <span
        className="absolute inset-y-2 start-0 w-1 rounded-e"
        style={{ background: sev.color }}
        aria-hidden="true"
      />

      <div className="flex items-center gap-1.5 text-xs text-slate-300">
        <Icon name={cat.icon} className="w-3.5 h-3.5 shrink-0" style={{ color: cat.color }} />
        <span className="truncate" style={{ color: cat.color }}>{kicker}</span>
        <span className="text-slate-500" aria-hidden="true">·</span>
        <span style={{ color: sev.color }}>{t(`severity.${event.severity}`, { defaultValue: t('severity.low') })}</span>
        {sourceCount > 1 && (
          <>
            <span className="text-slate-500" aria-hidden="true">·</span>
            <span className="inline-flex items-center gap-1 text-slate-200">
              <Layers className="w-3 h-3" aria-hidden="true" />
              {t('events.sources', { count: sourceCount })}
            </span>
          </>
        )}
        <span className="flex-1" />
        <time className="shrink-0 text-slate-400" dateTime={event.event_date}>{timeAgo(event.event_date, t)}</time>
      </div>

      <h3 className="mt-1 text-[15px] font-semibold leading-snug text-slate-50 line-clamp-2">{event.title}</h3>

      <div className="mt-1.5 flex items-center gap-2 text-xs text-slate-400">
        {place && (
          <span className="inline-flex items-center gap-1 min-w-0" title={approx ? t('events.approx') : undefined}>
            {approx
              ? <CircleDashed className="w-3 h-3 shrink-0" aria-label={t('events.approx')} />
              : <MapPin className="w-3 h-3 shrink-0" aria-hidden="true" />}
            <span className="truncate">{flag && <span aria-hidden="true">{flag} </span>}{place}</span>
          </span>
        )}
        <span className="truncate"><bdi>{event.source_name || event.source}</bdi></span>
        <span className="flex-1" />
        <RiskPill score={event.risk_score} />
      </div>
    </article>
  );
}
