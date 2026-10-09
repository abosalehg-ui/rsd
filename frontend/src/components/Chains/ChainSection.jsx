/**
 * رصد - قسم «سلسلة الترابط» في لوحة تفاصيل الحدث.
 *
 * أسباب قصة الحدث المحتملة وآثارها (`/api/events/{id}/chain`)، كلٌّ بشارة ثقته
 * وعلاقته والقاعدة التي أنتجته. النقر على حدث مرتبط يفتحه في اللوحة نفسها.
 */
import React, { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { usePolling } from '../../hooks/usePolling';
import { getEventChain } from '../../utils/api';
import { pct } from '../../utils/chains';
import { ConfidenceBadge, LinkEvidence } from './LinkParts';

function LinkList({ title, items, onOpenEvent }) {
  const { t } = useTranslation();
  if (!items.length) return null;
  return (
    <div className="mt-2">
      <h4 className="text-2xs font-semibold uppercase tracking-wide text-slate-400">{title}</h4>
      <ul className="mt-1 space-y-2">
        {items.map(item => (
          <li key={item.id} className="rounded-md border border-rasad-border/70 bg-rasad-raised/40 px-2.5 py-2">
            {/* aria-label الزر يطغى على محتواه، فنسبة الثقة جزء منه لا من الشارة وحدها */}
            <button
              onClick={() => onOpenEvent?.(item.event.id)}
              className="w-full flex items-start gap-2 text-start text-sm text-slate-100 hover:text-cyan-200 focus-ring rounded"
              aria-label={t('chains.openEventConf', { title: item.event.title, confidence: pct(item.confidence) })}
            >
              <ConfidenceBadge value={item.confidence} className="mt-0.5" />
              <span className="min-w-0">
                <span className="line-clamp-2">{item.event.title}</span>
                <span className="block font-mono text-2xs text-slate-500">E{item.event.id}</span>
              </span>
            </button>
            <LinkEvidence link={item} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ChainSection({ eventId, onOpenEvent }) {
  const { t } = useTranslation();
  const valid = typeof eventId === 'number';
  const { data, error } = usePolling(
    useCallback(() => (valid ? getEventChain(eventId) : Promise.resolve(null)), [valid, eventId]),
    300000, [eventId],
  );
  if (!valid) return null;

  // استجابة حدث سابق (أثناء جلب الجديد) لا تُعرض
  const current = data && data.event_id === eventId ? data : null;
  const causes = current?.causes || [];
  const effects = current?.effects || [];

  return (
    <section className="mt-5" aria-labelledby="chain-section-title">
      <h3 id="chain-section-title" className="text-xs font-semibold text-slate-300">{t('chains.drawerTitle')}</h3>
      {!current ? (
        <p className="mt-2 text-xs text-slate-400" role={error ? 'alert' : undefined}>
          {error ? t('chains.loadFailed') : t('chains.loading')}
        </p>
      ) : causes.length + effects.length === 0 ? (
        <p className="mt-2 text-xs text-slate-400">{t('chains.none')}</p>
      ) : (
        <>
          <LinkList title={t('chains.causes')} items={causes} onOpenEvent={onOpenEvent} />
          <LinkList title={t('chains.effects')} items={effects} onOpenEvent={onOpenEvent} />
        </>
      )}
      <p className="mt-2 text-2xs leading-relaxed text-slate-500">{t('chains.note')}</p>
    </section>
  );
}
