/**
 * رصد - مؤشر استخبارات الدول (Country Intelligence Index) v1.3
 *
 * يستهلك /api/events/country-index ويعرض ترتيب الدول مع شريط درجة
 * وتوزيع التصنيفات والخطورة لكل دولة.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';
import { COUNTRIES, CATEGORIES } from '../../utils/constants';

function scoreColor(score) {
  if (score >= 75) return '#ef4444';
  if (score >= 50) return '#f59e0b';
  if (score >= 25) return '#facc15';
  return '#10b981';
}

export default function CountryIndex({ data }) {
  const { t } = useTranslation();
  const ranking = data?.ranking || [];

  if (ranking.length === 0) {
    return (
      <div className="bg-rasad-bg rounded-lg border border-rasad-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-xs font-bold text-slate-300">{t('stats.countryIndex')}</span>
        </div>
        <div className="text-[11px] text-slate-300 text-center py-3">{t('stats.noData')}</div>
      </div>
    );
  }

  return (
    <div className="bg-rasad-bg rounded-lg border border-rasad-border p-3">
      <div className="flex items-center gap-2 mb-1">
        <Activity className="w-3.5 h-3.5 text-cyan-400" />
        <span className="text-xs font-bold text-slate-300">{t('stats.countryIndex')}</span>
      </div>
      <div className="text-[11px] text-slate-300 mb-3">{t('stats.countryIndexDesc')}</div>
      <div className="space-y-2">
        {ranking.slice(0, 10).map((c, i) => {
          const info = COUNTRIES[c.country_code];
          const color = scoreColor(c.score);
          const topCat = Object.entries(c.by_category || {}).sort((a, b) => b[1] - a[1])[0];
          const topCatInfo = topCat ? (CATEGORIES[topCat[0]] || CATEGORIES.general) : null;
          return (
            <div key={c.country_code} className="bg-rasad-bg border border-rasad-border rounded p-2">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-mono text-slate-300 w-4">#{i + 1}</span>
                <span className="text-sm">{info?.flag || '🌍'}</span>
                <span className="text-[11px] text-slate-200 flex-1 truncate">{t(`countries.${c.country_code}`, { defaultValue: c.country_name || c.country_code })}</span>
                <span className="text-sm font-bold font-mono" style={{ color }}>{c.score}</span>
              </div>
              <div className="h-1.5 bg-rasad-border rounded-full overflow-hidden mb-1.5">
                <div className="h-full rounded-full transition-all duration-700" style={{ width: `${c.score}%`, background: color }} />
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-300">
                <span>
                  {c.by_severity?.critical ? <span className="text-red-400 ml-1">{c.by_severity.critical}❗</span> : null}
                  {c.by_severity?.high ? <span className="text-orange-400 ml-1">{c.by_severity.high}↑</span> : null}
                  {c.by_severity?.medium ? <span className="text-yellow-400 ml-1">{c.by_severity.medium}•</span> : null}
                  {c.by_severity?.low ? <span className="text-slate-300 ml-1">{c.by_severity.low}·</span> : null}
                </span>
                {topCatInfo && (
                  <span className="text-slate-300">
                    {topCatInfo.icon} {topCat[1]} / {c.total}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
