/**
 * رصد - مقياس مؤشر المخاطر النووية والإشعاعية.
 *
 * يُرسم كتدريج جهاز مسح إشعاعي: أربعة نطاقات ملوّنة (منخفض/متوسط/مرتفع/حرج
 * بحدود 30/55/75)، وإبرة عند القيمة، وعلامة باهتة عند قيمة الفترة السابقة —
 * فيُقرأ الرقم بموضعه واتجاهه لا مجردًا. تحته السلسلة الزمنية، ثم «كيف
 * حُسبت القيمة؟» تفكّ المعادلة بأرقامها الفعلية.
 *
 * التدريج `dir="ltr"`: المقاييس الرقمية تُقرأ من الصفر يسارًا في اللغتين.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Radiation, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { RISK_BANDS, SEVERITIES, riskColor, riskLevel } from '../../utils/constants';
import Sparkline from './Sparkline';

export function TrendNote({ delta, className = '' }) {
  const { t } = useTranslation();
  const d = Number(delta) || 0;
  const flat = Math.abs(d) < 0.5;
  const Icon = flat ? Minus : d > 0 ? ArrowUpRight : ArrowDownRight;
  const text = flat
    ? t('trend.flat')
    : t(d > 0 ? 'trend.up' : 'trend.down', { value: Math.abs(d).toFixed(1) });
  // الارتفاع في مؤشر خطر سيّئ: أحمر فاتح؛ الانخفاض أخضر
  const color = flat ? 'text-slate-300' : d > 0 ? 'text-red-300' : 'text-emerald-300';
  return (
    <span className={`inline-flex items-center gap-1 ${color} ${className}`}>
      <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
      <span>{text}</span>
    </span>
  );
}

export default function RiskGauge({ risk, loading = false, error = null, onRetry }) {
  const { t } = useTranslation();

  if (error && !risk) {
    return (
      <div className="rounded-lg border border-rasad-border bg-rasad-bg p-4 text-sm text-red-200" role="alert">
        {t('risk.loadFailed')}{' '}
        {onRetry && (
          <button onClick={onRetry} className="underline focus-ring rounded">{t('risk.retry')}</button>
        )}
      </div>
    );
  }
  if (!risk) {
    return <div className="shimmer h-40 rounded-lg" aria-busy={loading} aria-label={t('common.loading')} />;
  }

  const value = risk.index ?? 0;
  const level = risk.level || riskLevel(value);
  const color = SEVERITIES[level]?.color || riskColor(value);
  const c = risk.components || {};
  const pct = (v) => `${Math.max(0, Math.min(100, v))}%`;

  return (
    <section
      className="rounded-lg border border-rasad-border bg-rasad-bg p-4"
      aria-labelledby="risk-gauge-title"
    >
      <div className="flex items-center gap-2 text-hazard">
        <Radiation className="w-4 h-4" aria-hidden="true" />
        <h2 id="risk-gauge-title" className="text-sm font-semibold text-slate-100">{t('risk.title')}</h2>
      </div>

      <div className="mt-3 flex items-end justify-between gap-3 flex-wrap">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-5xl font-semibold leading-none tabular-nums" style={{ color }}>
            {value.toFixed(1)}
          </span>
          <span className="text-base font-semibold" style={{ color }}>{t(`risk.levels.${level}`)}</span>
        </div>
        <TrendNote delta={risk.delta} className="text-xs" />
      </div>

      {/* التدريج */}
      <div dir="ltr" className="mt-4">
        <div className="relative h-3 flex rounded-sm overflow-hidden" aria-hidden="true">
          {RISK_BANDS.map(b => (
            <div
              key={b.key}
              style={{ width: `${b.to - b.from}%`, background: `${SEVERITIES[b.key].color}${b.key === level ? 'cc' : '40'}` }}
            />
          ))}
        </div>
        <div className="relative h-4" aria-hidden="true">
          {/* علامة الفترة السابقة */}
          <span
            className="absolute top-0 w-px h-2.5 bg-slate-400/70"
            style={{ insetInlineStart: pct(risk.prev_index ?? 0) }}
            title={`${t('risk.prev')}: ${risk.prev_index ?? 0}`}
          />
          {/* الإبرة */}
          <span
            className="gauge-needle absolute -top-4 -translate-x-1/2 w-0 h-0 border-x-[6px] border-x-transparent border-t-[8px]"
            style={{ insetInlineStart: pct(value), borderTopColor: '#e6edf2' }}
          />
        </div>
        <div className="flex justify-between text-2xs font-mono text-slate-400 -mt-1.5">
          <span>0</span><span>30</span><span>55</span><span>75</span><span>100</span>
        </div>
      </div>
      <p className="sr-only">
        {t('risk.title')}: {value.toFixed(1)} — {t(`risk.levels.${level}`)}. {t('risk.prev')}: {risk.prev_index ?? 0}.
      </p>

      {risk.series?.length > 1 && (
        <div className="mt-3">
          <Sparkline
            points={risk.series.map(p => p.value)}
            color={color}
            label={t('risk.series')}
          />
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-300">
        <span>{t('risk.stories', { count: risk.stories ?? 0 })}</span>
        {risk.near_ksa_stories > 0 && (
          <span className="text-hazard-soft">{t('risk.nearKsa', { count: risk.near_ksa_stories })}</span>
        )}
      </div>

      <details className="mt-3 group">
        <summary className="cursor-pointer text-xs text-cyan-300 hover:text-cyan-200 focus-ring rounded w-fit">
          {t('risk.why')}
        </summary>
        <div className="mt-2 space-y-2 text-xs text-slate-300">
          <p className="leading-relaxed">
            {t('risk.formula', {
              maxW: Math.round((c.max_weight ?? 0.6) * 100),
              topW: Math.round((c.top_mean_weight ?? 0.4) * 100),
              n: c.top_n ?? 5,
              max: c.max ?? 0,
              mean: c.top_mean ?? 0,
            })}
          </p>
          <p className="text-slate-400">{t('risk.storiesNote')}</p>
        </div>
      </details>

      {risk.stories === 0 && <p className="mt-2 text-sm text-slate-300">{t('risk.empty')}</p>}
    </section>
  );
}
