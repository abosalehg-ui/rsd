/**
 * رصد - لوحة تفاصيل الحدث.
 *
 * كان الضغط على خبر يفتح توسيعًا صغيرًا داخل القائمة (وصف + رابط). هنا لوحة
 * تغطي العمود الجانبي: الوصف كاملًا، مصادر القصة كلها بروابطها، الموقع
 * ودقته والمسافة إلى المملكة، ومكوّنات درجة الخطر للأخبار النووية — كي يُفهم
 * لماذا صُنِّف الخبر كما صُنِّف. Escape يغلقها ويعيد التركيز لما قبلها.
 */
import React, { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { X, ExternalLink, Crosshair } from 'lucide-react';
import { categoryOf, ksaPlace, severityOf, timeAgo } from '../../utils/constants';
import { safeUrl } from '../../utils/security';
import { Icon } from '../../utils/icons';
import { RiskPill, placeLabel } from './EventCard';

const COMPONENT_ORDER = ['base', 'intensity', 'dampening', 'reassurance', 'statement', 'specificity', 'proximity'];

function RiskBreakdown({ nuclear }) {
  const { t } = useTranslation();
  const comps = nuclear?.components;
  if (!comps) return null;
  return (
    <section className="mt-5">
      <h3 className="text-xs font-semibold text-slate-300">{t('risk.breakdown')}</h3>
      <dl className="mt-2 space-y-1.5">
        {COMPONENT_ORDER.filter(k => comps[k]).map(k => {
          const v = comps[k];
          const positive = v > 0;
          return (
            <div key={k} className="grid grid-cols-[1fr_auto] items-center gap-3 text-xs">
              <dt className="text-slate-300">{t(`risk.components.${k}`)}</dt>
              <dd className={`font-mono tabular-nums ${positive ? 'text-slate-100' : 'text-emerald-300'}`}>
                {positive && k !== 'base' ? '+' : ''}{v}
              </dd>
            </div>
          );
        })}
        <div className="grid grid-cols-[1fr_auto] items-center gap-3 text-xs border-t border-rasad-border pt-1.5">
          <dt className="text-slate-300">{t('risk.components.source_trust')}</dt>
          <dd className="font-mono tabular-nums text-slate-100">×{comps.source_trust}</dd>
        </div>
      </dl>
    </section>
  );
}

function Row({ label, children }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-3 py-1.5 border-b border-rasad-border/60 text-sm">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-slate-100 min-w-0">{children}</dd>
    </div>
  );
}

export default function EventDrawer({ event, onClose, onShowOnMap, facilities = [] }) {
  const { t, i18n } = useTranslation();
  const closeRef = useRef(null);
  const returnFocus = useRef(null);

  useEffect(() => {
    if (!event) return undefined;
    returnFocus.current = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      returnFocus.current?.focus?.();
    };
  }, [event, onClose]);

  if (!event) return null;

  const cat = categoryOf(event.category);
  const sev = severityOf(event.severity);
  const nuclear = event.nuclear;
  const facility = facilities.find(f => f.id === event.facility_id);
  const link = safeUrl(event.url);
  const dateFmt = new Intl.DateTimeFormat(i18n.language === 'ar' ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB', {
    dateStyle: 'medium', timeStyle: 'short',
  });
  const fmt = (s) => (s ? dateFmt.format(new Date(s)) : '—');
  const sources = [
    { id: event.id, title: event.title, source_name: event.source_name || event.source, url: event.url, event_date: event.event_date },
    ...(event.story_related || []),
  ];
  const hasCoords = event.latitude != null && event.longitude != null;

  return (
    <div
      className="absolute inset-0 z-20 flex flex-col bg-rasad-panel"
      role="dialog"
      aria-modal="false"
      aria-labelledby="event-drawer-title"
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-rasad-border">
        <Icon name={cat.icon} className="w-4 h-4" style={{ color: cat.color }} />
        <span className="text-xs font-semibold text-slate-300">{t('events.details')}</span>
        <span className="flex-1" />
        <button
          ref={closeRef}
          onClick={onClose}
          aria-label={t('events.close')}
          className="min-w-11 min-h-11 -me-2 flex items-center justify-center rounded text-slate-300 hover:text-white hover:bg-rasad-border focus-ring"
        >
          <X className="w-5 h-5" aria-hidden="true" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded px-2 py-0.5" style={{ color: cat.color, background: `${cat.color}1f` }}>
            {event.topic ? t(`topics.${event.topic}`) : t(`categories.${event.category}`, { defaultValue: t('categories.general') })}
          </span>
          <span className="rounded px-2 py-0.5" style={{ color: sev.color, background: `${sev.color}1f` }}>
            {t(`severity.${event.severity}`, { defaultValue: t('severity.low') })}
          </span>
          <RiskPill score={event.risk_score} />
        </div>

        <h2 id="event-drawer-title" className="mt-3 text-lg font-semibold leading-snug text-slate-50">{event.title}</h2>

        <p className="mt-3 text-sm leading-relaxed text-slate-300">
          {event.description || <span className="text-slate-500">{t('events.noDescription')}</span>}
        </p>

        <dl className="mt-4">
          <Row label={t('events.published')}>{fmt(event.event_date)} <span className="text-slate-400">· {timeAgo(event.event_date, t)}</span></Row>
          {event.story_first_seen && event.story_first_seen !== event.event_date && (
            <Row label={t('events.firstSeen')}>{fmt(event.story_first_seen)}</Row>
          )}
          <Row label={t('events.location')}>
            {placeLabel(event, t) || '—'}
            <span className="block text-xs text-slate-400">{t(`events.precision.${event.geo_precision || 'none'}`)}</span>
          </Row>
          {facility && (
            <Row label={t('events.facility')}>{i18n.language === 'ar' ? facility.name_ar : facility.name_en}</Row>
          )}
          {nuclear?.distance_to_ksa_km != null && (
            <Row label={t('events.distanceKsa')}>
              <span className="font-mono tabular-nums">
                {t('facilities.distance', { km: Math.round(nuclear.distance_to_ksa_km), place: ksaPlace(nuclear, i18n.language) })}
              </span>
            </Row>
          )}
        </dl>

        <RiskBreakdown nuclear={nuclear} />

        <section className="mt-5">
          <h3 className="text-xs font-semibold text-slate-300">
            {t('events.sourcesTitle')} <span className="font-mono text-slate-500">{sources.length}</span>
          </h3>
          <ul className="mt-2 space-y-2">
            {sources.map(s => {
              const href = safeUrl(s.url);
              return (
                <li key={s.id} className="text-sm">
                  {href ? (
                    <a href={href} target="_blank" rel="noopener noreferrer"
                      className="group inline-flex items-start gap-1.5 text-slate-200 hover:text-cyan-200 focus-ring rounded">
                      <ExternalLink className="w-3.5 h-3.5 mt-1 shrink-0 text-slate-500 group-hover:text-cyan-300" aria-hidden="true" />
                      <span>
                        <bdi className="font-semibold">{s.source_name}</bdi>
                        {s.id !== event.id && <span className="block text-xs text-slate-400 line-clamp-2">{s.title}</span>}
                      </span>
                    </a>
                  ) : (
                    <bdi className="font-semibold text-slate-300">{s.source_name}</bdi>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      <div className="flex gap-2 px-4 py-3 border-t border-rasad-border">
        {hasCoords && (
          <button
            onClick={() => onShowOnMap?.(event)}
            className="flex-1 min-h-11 inline-flex items-center justify-center gap-2 rounded-md bg-rasad-raised border border-rasad-border text-sm text-slate-100 hover:border-cyan-500 focus-ring"
          >
            <Crosshair className="w-4 h-4" aria-hidden="true" /> {t('events.viewOnMap')}
          </button>
        )}
        {link && (
          <a
            href={link} target="_blank" rel="noopener noreferrer"
            className="flex-1 min-h-11 inline-flex items-center justify-center gap-2 rounded-md bg-cyan-500/15 border border-cyan-500/40 text-sm text-cyan-100 hover:bg-cyan-500/25 focus-ring"
          >
            <ExternalLink className="w-4 h-4" aria-hidden="true" /> {t('events.openSource')}
          </a>
        )}
      </div>
    </div>
  );
}
