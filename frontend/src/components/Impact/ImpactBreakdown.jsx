/**
 * رصد - تفكيك درجة الأثر على المملكة لحدث واحد.
 *
 * الدرجة = 100 × الشدة × القرب × الإشارة المباشرة × ثقة المصدر. تُعرض المعادلة
 * بأرقامها الفعلية ومع كل معامل سببه (المسافة، العبارة المذكورة…) — كما تُعرض
 * مكوّنات درجة الخطر النووي، فلا تُقرأ الدرجة رقمًا مجردًا.
 *
 * الأرقام `dir="ltr"` كي لا تنقلب المعادلة في الواجهة العربية.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { IMPACT_SECTORS, ksaPlace, riskColor } from '../../utils/constants';
import { Icon } from '../../utils/icons';

const FACTOR_ORDER = ['severity', 'proximity', 'mention', 'source_trust'];

const fmtFactor = (v) => (Number.isFinite(v) ? String(Number(v.toFixed(2))) : '—');

/** «90 = 100 × 1 × 1 × 1 × 0.9» */
export function ImpactFormula({ impact, score, className = '' }) {
  const c = impact?.components;
  if (!c) return null;
  const value = score ?? impact.score ?? 0;
  return (
    <span dir="ltr" className={`font-mono tabular-nums ${className}`}>
      {Number(value).toFixed(1)} = 100 × {FACTOR_ORDER.map(k => fmtFactor(c[k])).join(' × ')}
    </span>
  );
}

export function ImpactPill({ score, className = '' }) {
  const { t } = useTranslation();
  if (score === null || score === undefined) return null;
  const color = riskColor(score);
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-xs font-semibold tabular-nums ${className}`}
      style={{ color, background: `${color}1f`, boxShadow: `inset 0 0 0 1px ${color}55` }}
      title={t('impact.score')}
    >
      {Math.round(score)}
    </span>
  );
}

export function SectorChips({ sectors = [], className = '' }) {
  const { t } = useTranslation();
  if (!sectors.length) return null;
  return (
    <span className={`inline-flex flex-wrap gap-1 ${className}`}>
      {sectors.map(key => {
        const s = IMPACT_SECTORS[key];
        if (!s) return null;
        return (
          <span
            key={key}
            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-2xs"
            style={{ color: s.color, background: `${s.color}1a` }}
          >
            <Icon name={s.icon} className="w-3 h-3" />
            {t(`impact.sectors.${key}`)}
          </span>
        );
      })}
    </span>
  );
}

/** سبب كل معامل بالكلمات: «حرج»، «قريب (أقل من 800 كم) — 412 كم من جازان»… */
function factorReason(key, impact, t, lang) {
  switch (key) {
    case 'severity':
      return t(`severity.${impact.severity}`, { defaultValue: impact.severity });
    case 'proximity': {
      const band = t(`impact.bands.${impact.proximity_band}`, { defaultValue: impact.proximity_band });
      if (impact.distance_to_ksa_km == null) return band;
      const place = ksaPlace(impact, lang);
      return `${band} — ${t('facilities.distance', { km: Math.round(impact.distance_to_ksa_km), place })}`;
    }
    case 'mention': {
      const level = t(`impact.mentionLevels.${impact.mention}`, { defaultValue: impact.mention });
      return impact.mentioned?.length ? `${level} — ${impact.mentioned.join(lang === 'ar' ? '، ' : ', ')}` : level;
    }
    default:
      return '';
  }
}

export default function ImpactBreakdown({ event }) {
  const { t, i18n } = useTranslation();
  const impact = event?.impact;
  if (!impact?.components) return null;
  const score = event.ksa_impact ?? impact.score;

  return (
    <section className="mt-5" aria-labelledby="impact-breakdown-title">
      <div className="flex items-center justify-between gap-2">
        <h3 id="impact-breakdown-title" className="text-xs font-semibold text-slate-300">{t('impact.breakdown')}</h3>
        <ImpactPill score={score} />
      </div>
      <p className="mt-1 text-2xs text-slate-400">{t('impact.eventFormula')}</p>
      <dl className="mt-2 space-y-1.5">
        {FACTOR_ORDER.map(k => (
          <div key={k} className="grid grid-cols-[1fr_auto] items-start gap-3 text-xs">
            <dt className="text-slate-300 min-w-0">
              {t(`impact.components.${k}`)}
              {factorReason(k, impact, t, i18n.language) && (
                <span className="block text-2xs text-slate-400">{factorReason(k, impact, t, i18n.language)}</span>
              )}
            </dt>
            <dd dir="ltr" className="font-mono tabular-nums text-slate-100">×{fmtFactor(impact.components[k])}</dd>
          </div>
        ))}
        <div className="grid grid-cols-[1fr_auto] items-center gap-3 text-xs border-t border-rasad-border pt-1.5">
          <dt className="text-slate-300">{t('impact.score')}</dt>
          <dd><ImpactFormula impact={impact} score={score} className="text-slate-100" /></dd>
        </div>
      </dl>
      <div className="mt-2">
        {event.impact_sectors?.length
          ? <SectorChips sectors={event.impact_sectors} />
          : <span className="text-2xs text-slate-500">{t('impact.noSectors')}</span>}
      </div>
    </section>
  );
}
