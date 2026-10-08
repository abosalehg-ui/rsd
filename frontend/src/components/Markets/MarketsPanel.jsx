/**
 * رصد - لوحة الطاقة والأسواق.
 *
 * من الأعلى: تنبيه تاريخ البيانات (FRED يومي ومتأخّر — ليس لحظيًا) ← بطاقة
 * لكل سلسلة بقيمتها وتغيّرها وتاريخ ملاحظتها وخط مصغّر لتسعين يومًا ←
 * مخطط التزامن مع عبارة «قراءة تزامن وليست تنبؤًا ولا نصيحة مالية».
 *
 * بلا مفتاح: تعليمات التفعيل، وتبقى آخر القيم المخزّنة (إن وُجدت) ظاهرة.
 * كل القيم من قاعدة الخادم، فتعمل اللوحة دون اتصال بالإنترنت.
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { KeyRound, Info, AlertTriangle } from 'lucide-react';
import { usePolling } from '../../hooks/usePolling';
import { getMarketSeries, getMarketsCorrelation } from '../../utils/api';
import { MARKET_SERIES, THEME } from '../../utils/constants';
import { daysSince, formatObservedDate, formatQuote } from '../../utils/markets';
import Sparkline from '../Nuclear/Sparkline';
import { ChangeBadge } from './MarketTicker';
import SyncChart from './SyncChart';

export const SYNC_WINDOWS = [30, 60, 90];
// القيم يومية: استطلاع كل نصف ساعة يكفي ليلتقط جلب الخادم اليومي
const POLL_MS = 30 * 60 * 1000;

function NoKeyHint({ hasData }) {
  const { t } = useTranslation();
  return (
    <section role="note" aria-labelledby="markets-nokey-title" className="rounded-lg border border-hazard/40 bg-hazard-dim/40 p-3 text-xs">
      <h3 id="markets-nokey-title" className="flex items-center gap-1.5 font-semibold text-hazard-soft">
        <KeyRound className="w-3.5 h-3.5" aria-hidden="true" /> {t('markets.noKeyTitle')}
      </h3>
      <p className="mt-1.5 text-slate-200">{t('markets.noKeyBody')}</p>
      <code dir="ltr" className="mt-1.5 block rounded bg-rasad-bg px-2 py-1 font-mono text-slate-100">FRED_API_KEY=…</code>
      <p className="mt-1.5 text-slate-400">{t('markets.noKeyWhere')}</p>
      {hasData && <p className="mt-1.5 text-slate-300">{t('markets.noKeyStale')}</p>}
    </section>
  );
}

function DataDateNote({ latest }) {
  const { t, i18n } = useTranslation();
  const age = daysSince(latest.as_of);
  const fetched = latest.fetched_at
    ? new Date(latest.fetched_at).toLocaleString(i18n.language === 'ar' ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
    })
    : null;
  return (
    <p className="flex items-start gap-1.5 rounded border border-rasad-border bg-rasad-bg/60 px-2.5 py-2 text-2xs text-slate-300">
      <Info className="w-3.5 h-3.5 shrink-0 mt-px text-slate-400" aria-hidden="true" />
      <span>
        <span className="font-semibold text-slate-100">
          {t('markets.dataDate', { date: formatObservedDate(latest.as_of, i18n.language) })}
        </span>
        {age != null && age > 0 && <> · {t('markets.daysOld', { count: age })}</>}
        {' — '}{t('markets.lagNote')}
        {fetched && <> {t('markets.fetchedAt', { time: fetched })}</>}
      </span>
    </p>
  );
}

function QuoteCard({ quote, points }) {
  const { t, i18n } = useTranslation();
  const values = (points || []).map(p => p.value);
  const lo = values.length ? Math.min(...values) : 0;
  const hi = values.length ? Math.max(...values) : 1;
  const name = t(`markets.series.${quote.code}`);
  return (
    <li className="rounded-lg border border-rasad-border bg-rasad-bg/40 p-2.5" aria-label={name}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs text-slate-300 truncate">{name}</span>
        <span className="text-2xs text-slate-500">{t(`markets.units.${quote.unit}`, { defaultValue: quote.unit })}</span>
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-mono text-lg font-semibold tabular-nums text-slate-50" dir="ltr">{formatQuote(quote.value)}</span>
        <ChangeBadge pct={quote.change_pct} className="text-xs" />
      </div>
      <div className="text-2xs text-slate-500">
        {quote.observed_at
          ? t('markets.observed', { date: formatObservedDate(quote.observed_at, i18n.language) })
          : t('markets.noValue')}
        {quote.prev_observed_at && (
          <> · {t('markets.vsPrev', { date: formatObservedDate(quote.prev_observed_at, i18n.language, { day: 'numeric', month: 'short' }) })}</>
        )}
      </div>
      {values.length > 1 && (
        <div className="mt-1.5 text-slate-300">
          <Sparkline
            points={values}
            min={lo}
            max={hi}
            color={THEME.textSecondary}
            height={28}
            label={t('markets.sparkLabel', { name, lo: formatQuote(lo), hi: formatQuote(hi), days: 90 })}
          />
        </div>
      )}
    </li>
  );
}

function CorrelationNote({ corr }) {
  const { t } = useTranslation();
  if (!corr) return null;
  const fmt = (pair) => (pair?.r == null
    ? t('markets.sync.rNone', { n: pair?.n ?? 0, min: corr.min_days })
    : t('markets.sync.r', { r: pair.r.toFixed(2), n: pair.n }));
  return (
    <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-2xs">
      <dt className="text-slate-400">{t('markets.sync.series.nuclear')} ↔ {t('markets.sync.series.brent')}</dt>
      <dd className="text-slate-200">{fmt(corr.nuclear_brent)}</dd>
      <dt className="text-slate-400">{t('markets.sync.series.ksa')} ↔ {t('markets.sync.series.brent')}</dt>
      <dd className="text-slate-200">{fmt(corr.ksa_brent)}</dd>
    </dl>
  );
}

export default function MarketsPanel({ latest, latestError = null }) {
  const { t, i18n } = useTranslation();
  const [days, setDays] = useState(30);
  const { data: seriesData } = usePolling(
    useCallback(() => getMarketSeries(MARKET_SERIES, 90), []),
    POLL_MS,
  );
  const { data: sync, error: syncError, loading: syncLoading } = usePolling(
    useCallback(() => getMarketsCorrelation(days), [days]),
    POLL_MS, [days],
  );

  if (!latest) {
    return (
      <div className="p-3 text-xs text-slate-400" role={latestError ? 'alert' : 'status'}>
        {latestError ? t('markets.loadFailed') : t('common.loading')}
      </div>
    );
  }

  const quotes = (latest.series || []).filter(q => q.value != null);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 space-y-3">
        <h2 className="text-sm font-semibold text-slate-100">{t('markets.title')}</h2>

        {!latest.enabled && <NoKeyHint hasData={latest.has_data} />}
        {latest.enabled && !latest.has_data && (
          <p className="text-xs text-slate-300" role="status">{t('markets.pending')}</p>
        )}

        {latest.has_data && <DataDateNote latest={latest} />}

        {quotes.length > 0 && (
          <ul className="grid grid-cols-2 gap-2" aria-label={t('markets.cardsLabel')}>
            {quotes.map(q => (
              <QuoteCard key={q.code} quote={q} points={seriesData?.series?.[q.code]} />
            ))}
          </ul>
        )}
      </div>

      <section className="border-t border-rasad-border p-3" aria-labelledby="markets-sync-title">
        <div className="flex items-center justify-between gap-2">
          <h3 id="markets-sync-title" className="text-xs font-semibold text-slate-200">{t('markets.sync.title')}</h3>
          <label className="sr-only" htmlFor="markets-sync-window">{t('markets.sync.window')}</label>
          <select
            id="markets-sync-window"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-rasad-bg border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
          >
            {SYNC_WINDOWS.map(d => <option key={d} value={d}>{t('markets.sync.days', { count: d })}</option>)}
          </select>
        </div>
        <p className="mt-1.5 flex items-start gap-1.5 rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1.5 text-xs font-semibold text-amber-200">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" aria-hidden="true" />
          {t('markets.sync.disclaimer')}
        </p>

        <div className={`mt-2 ${syncLoading && sync ? 'opacity-60' : ''}`}>
          {syncError && !sync && (
            <p role="alert" className="text-xs text-red-300">{t('markets.sync.loadFailed')}</p>
          )}
          {sync && (
            <>
              <SyncChart points={sync.points || []} />
              <CorrelationNote corr={sync.correlation} />
              <p className="mt-2 text-2xs text-slate-400">
                {t('markets.sync.method')}
                {sync.coverage_start && (
                  <> {t('markets.sync.coverage', { date: formatObservedDate(sync.coverage_start, i18n.language) })}</>
                )}
                {sync.brent_as_of && (
                  <> {t('markets.sync.brentAsOf', { date: formatObservedDate(sync.brent_as_of, i18n.language) })}</>
                )}
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
