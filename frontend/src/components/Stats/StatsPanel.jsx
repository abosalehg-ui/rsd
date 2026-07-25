/**
 * رصد - لوحة الإحصائيات
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CATEGORIES, COUNTRIES, formatNumber } from '../../utils/constants';
import { BarChart3, TrendingUp, Globe, AlertTriangle } from 'lucide-react';
import CountryIndex from './CountryIndex';

export default function StatsPanel({ stats, countryIndex }) {
  const { t } = useTranslation();
  if (!stats) return <div className="shimmer h-full" />;

  const escalation = stats.escalation_index || 0;
  const escColor = escalation > 30 ? '#ef4444' : escalation > 15 ? '#f59e0b' : '#10b981';

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-y-auto">
      {/* مؤشر التصعيد */}
      <div className="bg-rasad-bg rounded-lg border border-rasad-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4" style={{ color: escColor }} />
          <span className="text-xs font-bold text-slate-200">{t('stats.escalationIndex')}</span>
        </div>
        <div className="flex items-end gap-3">
          <span className="text-3xl font-bold font-mono" style={{ color: escColor }}>{escalation}%</span>
          <div className="flex-1 h-2 bg-rasad-border rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${Math.min(escalation, 100)}%`, background: escColor }} />
          </div>
        </div>
      </div>

      {/* إحصائيات سريعة */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-rasad-bg rounded border border-rasad-border p-2 text-center">
          <div className="text-lg font-bold font-mono text-white">{formatNumber(stats.total)}</div>
          <div className="text-[11px] text-slate-300">{t('stats.totalEvents')}</div>
        </div>
        <div className="bg-rasad-bg rounded border border-rasad-border p-2 text-center">
          <div className="text-lg font-bold font-mono text-red-400">{formatNumber(stats.categories?.military || 0)}</div>
          <div className="text-[11px] text-slate-300">{t('stats.militaryEvents')}</div>
        </div>
      </div>

      {/* مؤشر استخبارات الدول (v1.3) */}
      <CountryIndex data={countryIndex} />

      {/* التوزيع حسب التصنيف */}
      <div className="bg-rasad-bg rounded-lg border border-rasad-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-xs font-bold text-slate-300">{t('stats.byCategory')}</span>
        </div>
        <div className="space-y-1.5">
          {Object.entries(CATEGORIES).map(([key, cat]) => {
            const count = stats.categories?.[key] || 0;
            const pct = stats.total ? Math.round((count / stats.total) * 100) : 0;
            return (
              <div key={key} className="flex items-center gap-2">
                <span className="text-xs w-5">{cat.icon}</span>
                <span className="text-[11px] text-slate-300 w-16">{t(`categories.${key}`)}</span>
                <div className="flex-1 h-1.5 bg-rasad-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, background: cat.color }} />
                </div>
                <span className="text-[11px] font-mono text-slate-300 w-8 text-left">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* التوزيع حسب الدولة */}
      <div className="bg-rasad-bg rounded-lg border border-rasad-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <Globe className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-xs font-bold text-slate-300">{t('stats.byCountry')}</span>
        </div>
        <div className="space-y-1">
          {(stats.countries || []).slice(0, 8).map(c => {
            const info = COUNTRIES[c.code];
            const pct = stats.total ? Math.round((c.count / stats.total) * 100) : 0;
            return (
              <div key={c.code} className="flex items-center gap-2">
                <span className="text-xs">{info?.flag || '🌍'}</span>
                <span className="text-[11px] text-slate-300 flex-1">{t(`countries.${c.code}`, { defaultValue: c.name || c.code })}</span>
                <div className="w-16 h-1.5 bg-rasad-border rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-cyan-500" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-[11px] font-mono text-slate-300 w-6 text-left">{c.count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* المصادر */}
      <div className="bg-rasad-bg rounded-lg border border-rasad-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-xs font-bold text-slate-300">{t('stats.bySource')}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(stats.sources || {}).map(([src, count]) => (
            <span key={src} className="text-[11px] px-2 py-0.5 rounded bg-rasad-border text-slate-300">
              {src} <span className="font-mono text-cyan-400">{count}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
