/**
 * رصد - لوحة متابعة إيران OSINT
 * مستوحاة من: iranstrikemap.com + live-iran-map.com
 */
import React, { useState, useEffect } from 'react';
import { getIranStrikes, getIranLeaders, getIranStats } from '../../utils/api';
import { CONFIDENCE, IRAN_EVENT_TYPES, timeAgo } from '../../utils/constants';
import { Target, Users, RefreshCw } from 'lucide-react';

const CONF_TABS = [
  { id: 'all', label: 'الكل' },
  { id: 'HIGH', label: '🟢 موثوق' },
  { id: 'MEDIUM', label: '🟡 متوسط' },
  { id: 'LOW', label: '🔵 غير مؤكد' },
];

export default function IranPanel({ onSelectStrike }) {
  const [tab, setTab] = useState('strikes');
  const [confFilter, setConfFilter] = useState('all');
  const [strikes, setStrikes] = useState([]);
  const [leaders, setLeaders] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [strikesData, leadersData, statsData] = await Promise.all([
        getIranStrikes({ hours: 72, limit: 50 }),
        getIranLeaders(72),
        getIranStats(72),
      ]);
      setStrikes(strikesData?.strikes || []);
      setLeaders(leadersData?.leaders || []);
      setStats(statsData);
    } catch (e) {
      console.error('Iran panel error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const filteredStrikes = confFilter === 'all'
    ? strikes
    : strikes.filter(s => s.confidence === confFilter);

  return (
    <div className="flex flex-col h-full bg-[#0d1117] text-white font-arabic">
      {/* رأس اللوحة */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e293b] bg-[#111827]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🇮🇷</span>
          <span className="font-bold text-sm text-red-400">متابعة إيران OSINT</span>
          <span className="text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full border border-red-500/30 animate-pulse">
            LIVE
          </span>
        </div>
        <button onClick={loadData} className="text-slate-400 hover:text-white">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* إحصائيات سريعة */}
      {stats && (
        <div className="grid grid-cols-3 gap-2 p-3 border-b border-[#1e293b]">
          {[
            { label: 'إجمالي', value: stats.total, color: 'text-white' },
            { label: '🟢 موثوق', value: stats.by_confidence?.HIGH || 0, color: 'text-green-400' },
            { label: '💥 ضربات', value: stats.by_type?.strike || 0, color: 'text-red-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-[#1a2236] rounded-lg p-2 text-center">
              <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
              <div className="text-[10px] text-slate-500">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* تبويبات */}
      <div className="flex border-b border-[#1e293b]">
        {[
          { id: 'strikes', label: 'الضربات', icon: <Target className="w-3 h-3" /> },
          { id: 'leaders', label: 'القادة', icon: <Users className="w-3 h-3" /> },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2.5 text-xs transition-colors ${
              tab === t.id
                ? 'text-red-400 border-b-2 border-red-400 bg-red-400/5'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* محتوى التبويبات */}
      <div className="flex-1 overflow-y-auto">

        {/* تبويب الضربات */}
        {tab === 'strikes' && (
          <div>
            {/* فلتر الثقة */}
            <div className="flex gap-1 p-2 overflow-x-auto">
              {CONF_TABS.map(ct => (
                <button
                  key={ct.id}
                  onClick={() => setConfFilter(ct.id)}
                  className={`text-[10px] px-2 py-1 rounded whitespace-nowrap transition-colors ${
                    confFilter === ct.id
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-[#1a2236] text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {ct.label}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="text-center py-8 text-slate-500 text-sm">جارٍ التحميل...</div>
            ) : filteredStrikes.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">لا توجد بيانات</div>
            ) : (
              filteredStrikes.map(strike => {
                const conf = CONFIDENCE[strike.confidence] || CONFIDENCE.LOW;
                const evType = IRAN_EVENT_TYPES[strike.event_type] || IRAN_EVENT_TYPES.strike;
                return (
                  <div
                    key={strike.id}
                    onClick={() => onSelectStrike?.(strike)}
                    className="border-b border-[#1e293b] px-3 py-2.5 hover:bg-[#1a2236] cursor-pointer group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        {/* بادجات */}
                        <div className="flex items-center gap-1 mb-1 flex-wrap">
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded border font-bold"
                            style={{ color: conf.color, borderColor: conf.color + '40', background: conf.color + '15' }}
                          >
                            {conf.icon} {conf.label}
                          </span>
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded"
                            style={{ color: evType.color, background: evType.color + '20' }}
                          >
                            {evType.icon} {evType.label}
                          </span>
                          {strike.video_url && (
                            <a
                              href={strike.video_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 hover:bg-purple-500/30"
                            >
                              🎥 فيديو
                            </a>
                          )}
                        </div>
                        {/* العنوان */}
                        <p className="text-xs text-slate-200 leading-relaxed line-clamp-2 group-hover:text-white">
                          {strike.title}
                        </p>
                        {/* المعلومات السفلية */}
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-slate-500">{strike.location_name || strike.country}</span>
                          <span className="text-[10px] text-slate-600">•</span>
                          <span className="text-[10px] text-slate-500">{timeAgo(strike.event_date)}</span>
                          {strike.url && (
                            <a
                              href={strike.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="text-[10px] text-cyan-500 hover:text-cyan-400 mr-auto"
                            >
                              المصدر ←
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
          <div className="p-2">
            {leaders.map(leader => (
              <div
                key={leader.id}
                className={`mb-2 rounded-lg border p-3 transition-colors ${
                  leader.active
                    ? 'border-red-500/30 bg-red-500/5'
                    : 'border-[#1e293b] bg-[#1a2236]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span>{leader.icon}</span>
                    <div>
                      <div className="text-xs font-bold text-white">{leader.name}</div>
                      <div className="text-[10px] text-slate-400">{leader.role}</div>
                    </div>
                  </div>
                  {leader.active && (
                    <span className="text-[9px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded-full border border-red-500/30">
                      نشط
                    </span>
                  )}
                </div>
                {leader.recent_news.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {leader.recent_news.slice(0, 2).map((n, i) => (
                      <a
                        key={i}
                        href={n.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-[10px] text-slate-400 hover:text-cyan-400 truncate"
                      >
                        → {n.title}
                      </a>
                    ))}
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
