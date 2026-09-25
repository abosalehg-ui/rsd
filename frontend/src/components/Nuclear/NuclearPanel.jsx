/**
 * رصد - لوحة الرصد النووي والإشعاعي (التبويب الافتراضي).
 *
 * من الأعلى: مقياس المؤشر ← فلاتر الموضوع والقرب من المملكة ← المنشآت
 * المذكورة ← قائمة القصص. المؤشر يأتي من App (يشاركه الهيدر)؛ القصص والمنشآت
 * تُجلب هنا لأنها تخص هذه اللوحة وحدها.
 */
import React, { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { usePolling } from '../../hooks/usePolling';
import { getFacilityWatch, getNuclearEvents } from '../../utils/api';
import { NUCLEAR_TOPICS } from '../../utils/constants';
import RiskGauge from './RiskGauge';
import FacilityWatch from './FacilityWatch';
import StoryList from '../Events/StoryList';

const WINDOWS = [24, 72, 168];
const NEAR_KSA_KM = 800;

export default function NuclearPanel({
  risk, riskError, onRetryRisk, hours, onHoursChange, onOpenEvent, activeId, onSelectFacility,
}) {
  const { t } = useTranslation();
  const [topic, setTopic] = useState('');
  const [nearKsa, setNearKsa] = useState(false);

  const { data: eventsData, loading, error } = usePolling(
    useCallback(() => getNuclearEvents({
      hours, topic, limit: 120, near_ksa_km: nearKsa ? NEAR_KSA_KM : undefined,
    }), [hours, topic, nearKsa]),
    60000, [hours, topic, nearKsa],
  );
  const { data: watchData } = usePolling(
    useCallback(() => getFacilityWatch(hours), [hours]),
    300000, [hours],
  );

  const events = useMemo(() => eventsData?.events || [], [eventsData]);
  // الموضوعات الحاضرة في الفترة أولًا، بترتيب خطورتها
  const topicChips = useMemo(() => {
    const present = risk?.by_topic || {};
    return Object.keys(NUCLEAR_TOPICS).filter(k => present[k]);
  }, [risk]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="nuc-window" className="text-xs text-slate-400">{t('risk.window')}</label>
          <select
            id="nuc-window"
            value={hours}
            onChange={(e) => onHoursChange?.(Number(e.target.value))}
            className="bg-rasad-bg border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
          >
            {WINDOWS.map(h => <option key={h} value={h}>{t(`report.periods.${h}`)}</option>)}
          </select>
        </div>
        <RiskGauge risk={risk} error={riskError} onRetry={onRetryRisk} />
      </div>

      <div className="px-3 pb-2">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={t('risk.topics')}>
          <button
            onClick={() => setTopic('')}
            aria-pressed={!topic}
            className={`rounded-full px-2.5 py-1 text-xs focus-ring ${!topic ? 'bg-hazard-dim text-hazard-soft' : 'bg-rasad-raised text-slate-300 hover:text-white'}`}
          >
            {t('risk.allTopics')}
          </button>
          {topicChips.map(k => (
            <button
              key={k}
              onClick={() => setTopic(topic === k ? '' : k)}
              aria-pressed={topic === k}
              className={`rounded-full px-2.5 py-1 text-xs focus-ring ${topic === k ? 'bg-hazard-dim text-hazard-soft' : 'bg-rasad-raised text-slate-300 hover:text-white'}`}
            >
              {t(`topics.${k}`)} <span className="font-mono text-slate-500">{risk.by_topic[k].stories}</span>
            </button>
          ))}
        </div>
        <label className="mt-2 flex items-center gap-2 text-xs text-slate-300 cursor-pointer w-fit">
          <input
            type="checkbox"
            checked={nearKsa}
            onChange={(e) => setNearKsa(e.target.checked)}
            className="w-4 h-4 accent-yellow-400 focus-ring"
          />
          {t('risk.nearKsaOnly')}
        </label>
      </div>

      <div className="border-t border-rasad-border">
        <FacilityWatch facilities={watchData?.facilities || []} onSelect={onSelectFacility} />
      </div>

      <div className="border-t border-rasad-border">
        {error ? (
          <p className="px-4 py-6 text-sm text-red-200" role="alert">{t('news.loadFailed')}</p>
        ) : loading && events.length === 0 ? (
          <div className="p-3 space-y-2" aria-busy="true" aria-label={t('common.loading')}>
            {[0, 1, 2].map(i => <div key={i} className="shimmer h-20 rounded-lg" />)}
          </div>
        ) : events.length === 0 ? (
          <p className="px-4 py-6 text-sm text-slate-300">{t('risk.empty')}</p>
        ) : (
          <StoryList events={events} activeId={activeId} onOpen={onOpenEvent} />
        )}
      </div>
    </div>
  );
}
