/**
 * رصد - لوحة متابعة إيران OSINT
 * مستوحاة من: iranstrikemap.com + live-iran-map.com
 *
 * الضربات تصل كـ prop من `App` (الاستطلاع المشترك مع الخريطة). كانت اللوحة
 * تجلبها بنفسها بحدّ مختلف (50 مقابل 100) فتعرض قائمة تخالف ما على الخريطة،
 * مع طلب شبكة مكرّر. تبقى هنا القادة والإحصائيات فقط.
 */
import React, { useCallback, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getIranLeaders, getIranStats } from '../../utils/api';
import { CONFIDENCE, IRAN_EVENT_TYPES, timeAgo } from '../../utils/constants';
import { safeUrl } from '../../utils/security';
import { Target, Users, RefreshCw } from 'lucide-react';

const TABS = [
  { id: 'strikes', labelKey: 'iranPanel.strikes', Icon: Target },
  { id: 'leaders', labelKey: 'iranPanel.leaders', Icon: Users },
];

export default function IranPanel({ strikes = [], onSelectStrike }) {
  const { t } = useTranslation();
  const CONF_TABS = [
    { id: 'all', label: t('iranPanel.confAll') },
    { id: 'HIGH', label: t('iranPanel.confHigh') },
    { id: 'MEDIUM', label: t('iranPanel.confMedium') },
    { id: 'LOW', label: t('iranPanel.confLow') },
  ];
  const [tab, setTab] = useState('strikes');
  const [confFilter, setConfFilter] = useState('all');
  const [leaders, setLeaders] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [leadersData, statsData] = await Promise.all([
        getIranLeaders(72),
        getIranStats(72),
      ]);
      setLeaders(leadersData?.leaders || []);
      setStats(statsData);
      setError(null);
    } catch (e) {
      // كان الخطأ يُبتلَع فيظهر "لا توجد بيانات" رغم أن الخادم غير متاح
      console.error('Iran panel error:', e);
      setError(e?.message || 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  // تأجيل الاستدعاء خارج دورة العرض (تفادي setState متزامن داخل التأثير)
  useEffect(() => {
    const id = setTimeout(loadData, 0);
    return () => clearTimeout(id);
  }, [loadData]);

  const filteredStrikes = confFilter === 'all'
    ? strikes
    : strikes.filter(s => s.confidence === confFilter);

  return (
    <div className="flex flex-col h-full bg-rasad-bg text-white font-arabic">
      {/* رأس اللوحة */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-rasad-border bg-rasad-panel">
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden="true">🇮🇷</span>
          <span className="font-bold text-sm text-red-400">{t('iranPanel.title')}</span>
          <span className="text-2xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full border border-red-500/30 animate-pulse">
            LIVE
          </span>
        </div>
        <button onClick={loadData} aria-label={t('iranPanel.reload')} title={t('iranPanel.reload')}
          className="text-slate-300 hover:text-white focus-ring rounded min-w-11 min-h-11 flex items-center justify-center">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
        </button>
      </div>

      {/* إحصائيات سريعة */}
      {stats && (
        <div className="grid grid-cols-3 gap-2 p-3 border-b border-rasad-border">
          {[
            { label: t('iranPanel.total'), value: stats.total, color: 'text-white' },
            { label: t('iranPanel.trusted'), value: stats.by_confidence?.HIGH || 0, color: 'text-green-400' },
            { label: t('iranPanel.strikesCount'), value: stats.by_type?.strike || 0, color: 'text-red-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-rasad-panel rounded-lg p-2 text-center">
              <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
              <div className="text-2xs text-slate-300">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* تبويبات — أدوار ARIA كما في تبويبات App الرئيسية (كانت أزراراً عادية) */}
      <div className="flex border-b border-rasad-border" role="tablist" aria-label={t('iranPanel.title')}>
        {TABS.map(({ id, labelKey, Icon }) => {
          const active = tab === id;
          return (
            <button
              key={id}
              role="tab"
              id={`iran-tab-${id}`}
              aria-selected={active}
              aria-controls={`iran-tabpanel-${id}`}
              onClick={() => setTab(id)}
              className={`flex-1 flex items-center justify-center gap-1 py-2.5 text-xs transition-colors focus-ring ${
                active
                  ? 'text-red-400 border-b-2 border-red-400 bg-red-400/5'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Icon className="w-3 h-3" aria-hidden="true" /> {t(labelKey)}
            </button>
          );
        })}
      </div>

      {error && (
        <div role="alert" className="px-3 py-2 bg-red-500/10 border-b border-red-500/30 text-xs text-red-200 flex items-center justify-between gap-2">
          <span>{t('iranPanel.loadFailed')}</span>
          <button onClick={loadData} className="underline hover:text-white focus-ring rounded">{t('iranPanel.retry')}</button>
        </div>
      )}

      {/* محتوى التبويبات */}
      <div className="flex-1 overflow-y-auto">

        {/* تبويب الضربات */}
        {tab === 'strikes' && (
          <div role="tabpanel" id="iran-tabpanel-strikes" aria-labelledby="iran-tab-strikes">
            {/* فلتر الثقة */}
            <div className="flex gap-1 p-2 overflow-x-auto" role="group" aria-label={t('iranPanel.confAll')}>
              {CONF_TABS.map(ct => (
                <button
                  key={ct.id}
                  onClick={() => setConfFilter(ct.id)}
                  aria-pressed={confFilter === ct.id}
                  className={`text-2xs px-2 py-1 rounded whitespace-nowrap transition-colors focus-ring ${
                    confFilter === ct.id
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-rasad-panel text-slate-300 hover:text-white'
                  }`}
                >
                  {ct.label}
                </button>
              ))}
            </div>

            {filteredStrikes.length === 0 ? (
              <div className="text-center py-8 text-slate-300 text-sm">{t('iranPanel.noData')}</div>
            ) : (
              filteredStrikes.map(strike => {
                const conf = CONFIDENCE[strike.confidence] || CONFIDENCE.LOW;
                const evType = IRAN_EVENT_TYPES[strike.event_type] || IRAN_EVENT_TYPES.strike;
                const videoLink = safeUrl(strike.video_url);
                const sourceLink = safeUrl(strike.url);
                return (
                  <div
                    key={strike.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectStrike?.(strike)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectStrike?.(strike); } }}
                    className="border-b border-rasad-border px-3 py-2.5 hover:bg-rasad-panel cursor-pointer group focus-ring"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        {/* بادجات */}
                        <div className="flex items-center gap-1 mb-1 flex-wrap">
                          <span
                            className="text-2xs px-1.5 py-0.5 rounded border font-bold"
                            style={{ color: conf.color, borderColor: conf.color + '40', background: conf.color + '15' }}
                          >
                            {conf.icon} {t(`confidence.${strike.confidence}`, { defaultValue: t('confidence.LOW') })}
                          </span>
                          <span
                            className="text-2xs px-1.5 py-0.5 rounded"
                            style={{ color: evType.color, background: evType.color + '20' }}
                          >
                            {evType.icon} {t(`iranEventTypes.${strike.event_type}`, { defaultValue: t('iranEventTypes.strike') })}
                          </span>
                          {videoLink && (
                            <a
                              href={videoLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="text-2xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 focus-ring"
                            >
                              {t('iranPanel.video')}
                            </a>
                          )}
                        </div>
                        {/* العنوان */}
                        <p className="text-xs text-slate-200 leading-relaxed line-clamp-2 group-hover:text-white">
                          {strike.title}
                        </p>
                        {/* المعلومات السفلية */}
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-2xs text-slate-300">{strike.location_name || strike.country}</span>
                          <span className="text-2xs text-slate-300" aria-hidden="true">•</span>
                          <span className="text-2xs text-slate-300">{timeAgo(strike.event_date, t)}</span>
                          {sourceLink && (
                            <a
                              href={sourceLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="text-2xs text-cyan-300 hover:text-cyan-200 ms-auto focus-ring rounded"
                            >
                              {t('iranPanel.source')}
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* تبويب القادة */}
        {tab === 'leaders' && (
          <div className="p-2" role="tabpanel" id="iran-tabpanel-leaders" aria-labelledby="iran-tab-leaders">
            {loading && leaders.length === 0 ? (
              <div className="space-y-2" aria-busy="true" aria-label={t('common.loading')}>
                {[0, 1, 2].map(i => <div key={i} className="shimmer h-16 rounded-lg" />)}
              </div>
            ) : leaders.map(leader => (
              <div
                key={leader.id}
                className={`mb-2 rounded-lg border p-3 transition-colors ${
                  leader.active
                    ? 'border-red-500/30 bg-red-500/5'
                    : 'border-rasad-border bg-rasad-panel'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span aria-hidden="true">{leader.icon}</span>
                    <div>
                      <div className="text-xs font-bold text-white">{leader.name}</div>
                      <div className="text-2xs text-slate-300">{leader.role}</div>
                    </div>
                  </div>
                  {leader.active && (
                    <span className="text-2xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded-full border border-red-500/30">
                      {t('iranPanel.active')}
                    </span>
                  )}
                </div>
                {leader.recent_news?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {leader.recent_news.slice(0, 2).map((n, i) => {
                      const link = safeUrl(n.url);
                      return link ? (
                        <a
                          key={i}
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-2xs text-slate-300 hover:text-cyan-400 truncate focus-ring rounded"
                        >
                          → {n.title}
                        </a>
                      ) : (
                        <span key={i} className="block text-2xs text-slate-300 truncate">→ {n.title}</span>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
