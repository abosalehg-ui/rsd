/**
 * رصد - نافذة «سلاسل التأثير»: أطول سلاسل «سبب ← أثر» في الفترة.
 *
 * كل سلسلة عقدٌ (قصص) بينها روابط بنسبة ثقة وعلاقة وقاعدة. مفتاح «إخفاء
 * الروابط ضعيفة الثقة» يعيد بناء السلاسل على الخادم دون الروابط الأضعف — فتنقسم
 * السلسلة عند حلقتها الضعيفة بدل أن تُعرض كاملة بثقة مضلِّلة.
 */
import React, { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Workflow } from 'lucide-react';
import { usePolling } from '../../hooks/usePolling';
import { useModal } from '../../hooks/useModal';
import { getChains } from '../../utils/api';
import { LOW_CONFIDENCE, pct } from '../../utils/chains';
import { ConfidenceBadge, LinkEvidence } from './LinkParts';
import StaleNotice, { staleClass } from '../common/StaleNotice';

const PERIODS = [24, 72, 168];

/** `confidence`: ثقة الرابط الواصل إلى هذه العقدة — تُنطق مع اسم الزر لأن
 * aria-label الزر يطغى على محتواه. */
function Node({ node, confidence, onOpenEvent }) {
  const { t } = useTranslation();
  return (
    <button
      onClick={() => onOpenEvent?.(node.id)}
      className="w-full text-start rounded-md border border-rasad-border bg-rasad-raised/60 px-3 py-2 hover:border-cyan-500 focus-ring"
      aria-label={confidence == null
        ? t('chains.openEvent', { title: node.title })
        : t('chains.openEventConf', { title: node.title, confidence: pct(confidence) })}
    >
      <span className="block text-sm font-semibold text-slate-100 line-clamp-2">{node.title}</span>
      <span className="block text-2xs text-slate-400">
        <span className="font-mono">E{node.id}</span>
        {node.source_name && <> · <bdi>{node.source_name}</bdi></>}
      </span>
    </button>
  );
}

function Chain({ chain, onOpenEvent }) {
  const { t } = useTranslation();
  return (
    <li className="rounded-lg border border-rasad-border p-3">
      <div className="flex items-center gap-2 text-2xs text-slate-400">
        <span>{t('chains.chainLength', { count: chain.length })}</span>
        <span className="flex-1" />
        <span>{t('chains.chainConfidence')}</span>
        <ConfidenceBadge value={chain.confidence} />
      </div>
      <ol className="mt-2 space-y-1.5">
        {chain.nodes.map((node, i) => (
          <li key={node.id}>
            {i > 0 && (
              <div className="flex items-start gap-2 ps-3 py-1">
                <span className="text-cyan-300 text-sm leading-5" aria-hidden="true">{t('chains.arrowDown')}</span>
                <span className="min-w-0 flex-1">
                  <span className="inline-flex items-center gap-2">
                    <ConfidenceBadge value={chain.links[i - 1].confidence} />
                  </span>
                  <LinkEvidence link={chain.links[i - 1]} />
                </span>
              </div>
            )}
            <Node node={node} confidence={i > 0 ? chain.links[i - 1].confidence : null} onOpenEvent={onOpenEvent} />
          </li>
        ))}
      </ol>
    </li>
  );
}

export default function ChainsModal({ open, onClose, onOpenEvent }) {
  const { t } = useTranslation();
  const [hours, setHours] = useState(72);
  const [hideLow, setHideLow] = useState(false);
  const closeRef = useRef(null);
  const dialogRef = useRef(null);

  const { data, error, loading, stale, refetch } = usePolling(
    useCallback(
      () => (open ? getChains(hours, hideLow ? LOW_CONFIDENCE : undefined) : Promise.resolve(null)),
      [open, hours, hideLow],
    ),
    300000, [open, hours, hideLow],
  );

  useModal(open, onClose, { containerRef: dialogRef, initialFocusRef: closeRef });

  if (!open) return null;

  const chains = data?.chains || [];

  return (
    <div ref={dialogRef} className="fixed inset-0 z-[10000] bg-black/70 flex items-start justify-center overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="chains-title">
      <div className="w-full max-w-2xl my-0 sm:my-6 min-h-full sm:min-h-0 bg-rasad-panel sm:rounded-xl border border-rasad-border shadow-2xl">
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 px-4 py-3 bg-rasad-panel/95 backdrop-blur border-b border-rasad-border sm:rounded-t-xl">
          <Workflow className="w-4 h-4 text-cyan-300" aria-hidden="true" />
          <h2 id="chains-title" className="text-sm font-semibold text-slate-50">{t('chains.title')}</h2>
          <span className="flex-1" />
          <label htmlFor="chains-period" className="text-xs text-slate-400">{t('chains.period')}</label>
          <select
            id="chains-period" value={hours} onChange={e => setHours(Number(e.target.value))}
            className="min-h-11 bg-rasad-bg border border-rasad-border rounded px-2 py-2 text-xs text-slate-100 focus-ring"
          >
            {PERIODS.map(h => <option key={h} value={h}>{t(`chains.periods.${h}`)}</option>)}
          </select>
          <button ref={closeRef} onClick={onClose} aria-label={t('chains.close')}
            className="min-w-11 min-h-11 flex items-center justify-center rounded-md text-slate-300 hover:text-white hover:bg-rasad-border focus-ring">
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="px-4 sm:px-6 py-4">
          <label className="min-h-11 inline-flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
            <input
              type="checkbox" checked={hideLow} onChange={e => setHideLow(e.target.checked)}
              className="accent-cyan-500 w-4 h-4"
            />
            {t('chains.hideLow', { value: pct(LOW_CONFIDENCE) })}
          </label>

          {error && !data ? (
            <p className="mt-4 text-sm text-red-200" role="alert">{t('chains.loadFailed')}</p>
          ) : !data ? (
            <p className="mt-4 text-sm text-slate-300" aria-busy={loading}>{t('chains.loading')}</p>
          ) : (
            <>
              {/* فشل تحديث الفترة/المرشّح والسلاسل السابقة معروضة: نقول ذلك صراحةً */}
              <StaleNotice error={error} stale={stale} onRetry={refetch} className="mt-4" />
              {data.truncated && <p className="mt-3 text-2xs text-amber-200" role="note">{t('chains.truncated')}</p>}
              <div className={staleClass(stale)} aria-busy={stale && !error ? true : undefined}>
                {chains.length === 0 ? (
                  <p className="mt-4 text-sm text-slate-400">{t('chains.empty')}</p>
                ) : (
                  <ol className="mt-4 space-y-3">
                    {chains.map(c => <Chain key={c.links.map(l => l.id).join('-')} chain={c} onOpenEvent={onOpenEvent} />)}
                  </ol>
                )}
              </div>
            </>
          )}

          <p className="mt-5 text-2xs leading-relaxed text-slate-500">{t('chains.method')}</p>
        </div>
      </div>
    </div>
  );
}
