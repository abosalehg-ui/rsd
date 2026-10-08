/**
 * رصد - عدسة «الأثر على المملكة».
 *
 * من الأعلى: مقياس المؤشر (RiskGauge نفسه بصيغة المؤشر النووي) ← بنود «راقِب»
 * القاعدية ← أشرطة القطاعات ← الأحداث الأعلى أثرًا بمعادلة كل منها ← معاملات
 * المعادلة. كل رقم معروض بمكوّناته؛ لا درجة مجردة.
 *
 * النقر على قطاع يفتح شريط الأحداث مفلترًا به، والنقر على حدث يفتح لوحة
 * التفاصيل.
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Landmark, Eye, ArrowUpRight } from 'lucide-react';
import { usePolling } from '../../hooks/usePolling';
import { getEvent, getKsaImpact } from '../../utils/api';
import { IMPACT_SECTORS, riskColor } from '../../utils/constants';
import { Icon } from '../../utils/icons';
import RiskGauge, { TrendNote } from '../Nuclear/RiskGauge';
import { ImpactFormula, ImpactPill, SectorChips } from './ImpactBreakdown';

export const LENS_WINDOWS = [24, 48, 72, 168];
const FACTOR_TABLES = ['severity', 'proximity', 'mention'];

function SectorBars({ sectors, onSelectSector }) {
  const { t } = useTranslation();
  return (
    <>
    <div className="grid grid-cols-[7.5rem_1fr_auto] gap-2 px-1 text-2xs text-slate-500" aria-hidden="true">
      <span />
      <span />
      <span className="flex gap-1.5 justify-end">
        <span className="w-9 text-end">{t('impact.colIndex')}</span>
        <span className="w-6 text-end">{t('impact.colStories')}</span>
      </span>
    </div>
    <ul className="space-y-1.5">
      {sectors.map(s => {
        const meta = IMPACT_SECTORS[s.key];
        if (!meta) return null;
        const label = t(`impact.sectors.${s.key}`);
        const color = s.stories ? riskColor(s.index) : '#475569';
        return (
          <li key={s.key}>
            <button
              onClick={() => onSelectSector?.(s.key)}
              disabled={!onSelectSector}
              aria-label={`${label}: ${s.index.toFixed(1)} — ${t('impact.sectorStories', { count: s.stories })}`}
              title={onSelectSector ? t('impact.openSector', { sector: label }) : undefined}
              className="w-full grid grid-cols-[7.5rem_1fr_auto] items-center gap-2 rounded px-1 py-1 text-xs hover:bg-rasad-raised focus-ring disabled:hover:bg-transparent"
            >
              <span className="flex items-center gap-1.5 min-w-0 text-slate-200">
                <Icon name={meta.icon} className="w-3.5 h-3.5 shrink-0" style={{ color: meta.color }} />
                <span className="truncate">{label}</span>
              </span>
              <span className="relative h-2 rounded-sm bg-rasad-border/70 overflow-hidden" aria-hidden="true">
                <span
                  className="absolute inset-y-0 start-0 rounded-sm"
                  style={{ width: `${Math.max(0, Math.min(100, s.index))}%`, background: color }}
                />
              </span>
              <span className="flex items-center gap-1.5 justify-end">
                <span className="font-mono tabular-nums text-slate-100 w-9 text-end">{s.index.toFixed(0)}</span>
                <span className="font-mono text-2xs text-slate-500 w-6 text-end">{s.stories}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
    </>
  );
}

function WatchList({ items, topEvents, rule, onOpenEvent }) {
  const { t } = useTranslation();
  const byId = Object.fromEntries((topEvents || []).map(e => [e.id, e]));
  return (
    <section aria-labelledby="impact-watch-title" className="rounded-lg border border-hazard/30 bg-hazard-dim/40 p-3">
      <h3 id="impact-watch-title" className="flex items-center gap-1.5 text-xs font-semibold text-hazard-soft">
        <Eye className="w-3.5 h-3.5" aria-hidden="true" /> {t('impact.watchTitle')}
      </h3>
      {items.length === 0 ? (
        <p className="mt-1.5 text-xs text-slate-300">{t('impact.watchNone')}</p>
      ) : (
        <ul className="mt-1.5 space-y-1.5">
          {items.map(w => {
            const top = byId[w.top_event_id];
            // أبرز حدث في القطاع قد لا يكون بين العشرة الأعلى عمومًا: يُجلب برقمه
            const open = () => (top
              ? onOpenEvent?.(top)
              : getEvent(w.top_event_id).then(ev => onOpenEvent?.(ev)).catch(() => {}));
            return (
              <li key={w.key} className="text-xs text-slate-200">
                <span className="font-semibold">{t(`impact.sectors.${w.key}`)}</span>{' '}
                <span className="inline-flex items-center gap-0.5 text-red-300">
                  <ArrowUpRight className="w-3 h-3" aria-hidden="true" />
                  <span dir="ltr" className="font-mono">+{w.delta.toFixed(1)}</span>
                </span>{' '}
                <span className="text-slate-400">
                  {t('impact.watchItem', { prev: w.prev_index.toFixed(1), value: w.index.toFixed(1) })}
                </span>
                {w.top_event_id != null && (
                  <button
                    onClick={open}
                    className="block mt-0.5 text-start text-cyan-300 hover:text-cyan-200 underline-offset-2 hover:underline focus-ring rounded line-clamp-1"
                    title={t('impact.watchOpen')}
                  >
                    {top?.title || t('impact.watchOpen')}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <p className="mt-2 text-2xs text-slate-400">{rule}</p>
    </section>
  );
}

function TopEvents({ events, onOpenEvent, activeId }) {
  if (!events.length) return null;
  return (
    <ol className="divide-y divide-rasad-border/60">
      {events.map(ev => (
        <li key={ev.id}>
          <button
            onClick={() => onOpenEvent?.(ev)}
            aria-current={activeId === ev.id || undefined}
            className={`w-full text-start px-3 py-2.5 hover:bg-rasad-raised focus-ring ${activeId === ev.id ? 'bg-rasad-raised' : ''}`}
          >
            <span className="flex items-start gap-2">
              <ImpactPill score={ev.ksa_impact} className="shrink-0 mt-0.5" />
              <span className="min-w-0 flex-1">
                <span className="block text-sm text-slate-100 leading-snug line-clamp-2">{ev.title}</span>
                <ImpactFormula impact={ev.impact} score={ev.ksa_impact} className="block mt-1 text-2xs text-slate-400" />
                <SectorChips sectors={ev.impact_sectors || []} className="mt-1" />
              </span>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function FactorTables({ formula }) {
  const { t } = useTranslation();
  if (!formula) return null;
  const labelFor = {
    severity: (k) => t(`severity.${k}`),
    proximity: (k) => t(`impact.bands.${k}`),
    mention: (k) => t(`impact.mentionLevels.${k}`),
    source_trust: (k) => t(`impact.trust.${k}`, { defaultValue: k }),
  };
  return (
    <details className="group">
      <summary className="cursor-pointer text-xs text-cyan-300 hover:text-cyan-200 focus-ring rounded w-fit">
        {t('impact.factorsTitle')}
      </summary>
      <p className="mt-2 text-xs text-slate-200">{t('impact.eventFormula')}</p>
      <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
        {[...FACTOR_TABLES, 'source_trust'].map(key => (
          <table key={key} className="w-full text-2xs">
            <caption className="text-start text-xs font-semibold text-slate-300 pb-1">{t(`impact.components.${key}`)}</caption>
            <tbody>
              {Object.entries(formula[key] || {}).map(([k, v]) => (
                <tr key={k} className="border-b border-rasad-border/50">
                  <th scope="row" className="py-0.5 text-start font-normal text-slate-300">{labelFor[key](k)}</th>
                  <td dir="ltr" className="py-0.5 text-end font-mono tabular-nums text-slate-100">×{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
      </div>
      <p className="mt-2 text-2xs text-slate-400">{t('impact.method')}</p>
    </details>
  );
}

export default function KsaLens({ onOpenEvent, onSelectSector, activeId, initialHours = 48 }) {
  const { t } = useTranslation();
  const [hours, setHours] = useState(initialHours);
  const { data, error, loading, refetch } = usePolling(
    useCallback(() => getKsaImpact(hours), [hours]),
    60000, [hours],
  );

  const sectors = data?.sectors || [];
  const formula = data?.formula;

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="impact-window" className="text-xs text-slate-400">{t('impact.window')}</label>
          <select
            id="impact-window"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="bg-rasad-bg border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
          >
            {LENS_WINDOWS.map(h => <option key={h} value={h}>{t(`impact.periods.${h}`)}</option>)}
          </select>
        </div>

        <RiskGauge
          id="impact-gauge-title"
          risk={data}
          loading={loading}
          error={error}
          onRetry={refetch}
          title={t('impact.title')}
          icon={Landmark}
          formulaKey="impact.formula"
          noteKey="impact.storiesNote"
          emptyText={t('impact.empty')}
          loadFailedText={t('impact.loadFailed')}
          notes={<p className="text-slate-400">{t('impact.eventFormula')}</p>}
        />

        {data && (
          <WatchList
            items={data.watch || []}
            topEvents={data.top_events}
            onOpenEvent={onOpenEvent}
            rule={t('impact.watchRule', {
              delta: formula?.watch_min_delta ?? 10,
              min: formula?.watch_min_index ?? 25,
            })}
          />
        )}
      </div>

      {sectors.length > 0 && (
        <section className="px-3 pb-3" aria-labelledby="impact-sectors-title">
          <div className="flex items-center justify-between">
            <h3 id="impact-sectors-title" className="text-xs font-semibold text-slate-300">{t('impact.sectorsTitle')}</h3>
            {data && <TrendNote delta={data.delta} className="text-2xs" />}
          </div>
          <div className="mt-2">
            <SectorBars sectors={sectors} onSelectSector={onSelectSector} />
          </div>
        </section>
      )}

      {data?.top_events?.length > 0 && (
        <section className="border-t border-rasad-border" aria-labelledby="impact-top-title">
          <h3 id="impact-top-title" className="px-3 pt-3 pb-1 text-xs font-semibold text-slate-300">{t('impact.topTitle')}</h3>
          <TopEvents events={data.top_events} onOpenEvent={onOpenEvent} activeId={activeId} />
        </section>
      )}

      {formula && (
        <div className="border-t border-rasad-border px-3 py-3">
          <FactorTables formula={formula} />
        </div>
      )}
    </div>
  );
}
