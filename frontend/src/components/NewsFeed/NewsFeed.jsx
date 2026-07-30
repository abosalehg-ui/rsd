/**
 * رصد - قائمة الأحداث مع البحث والفلاتر
 *
 * الخلفية تدعم search / country_code / source / hours منذ البداية، ولم تكن
 * أيٌّ منها معروضة في الواجهة — أُضيفت هنا وموصولة بـ useFilters.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CATEGORIES, SEVERITIES, COUNTRIES, SOURCES, TIME_WINDOWS,
  categoryOf, severityOf, timeAgo,
} from '../../utils/constants';
import { safeUrl } from '../../utils/security';
import { Newspaper, ExternalLink, Filter, Search, X, RotateCcw } from 'lucide-react';

const SEARCH_DEBOUNCE_MS = 400;

export default function NewsFeed({ events = [], error, loading = false, onSelectEvent, filters, onFilterChange, onResetFilters }) {
  const { t } = useTranslation();
  const [expandedId, setExpandedId] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  // مسودة البحث محلية ثم تُدفع للفلتر بعد سكون — كي لا نطلق طلباً لكل حرف
  const [searchDraft, setSearchDraft] = useState(filters?.search || '');

  useEffect(() => {
    const id = setTimeout(() => {
      if (searchDraft !== (filters?.search || '')) onFilterChange?.('search', searchDraft);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [searchDraft, filters?.search, onFilterChange]);

  const activeFilterCount = ['category', 'severity', 'country_code', 'source', 'search']
    .filter(k => filters?.[k]).length;

  return (
    <div className="flex flex-col h-full">
      {/* العنوان */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-rasad-border">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-cyan-300" aria-hidden="true" />
          <span className="text-sm font-bold text-white">{t('news.title')}</span>
          <span className="text-xs font-mono bg-cyan-400/10 text-cyan-200 px-1.5 py-0.5 rounded">{events.length}</span>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="relative p-1.5 rounded hover:bg-rasad-border text-slate-300 hover:text-white focus-ring"
          aria-label={t('news.toggleFilters')}
          aria-expanded={showFilters}
        >
          <Filter className="w-4 h-4" aria-hidden="true" />
          {activeFilterCount > 0 && (
            <span className="absolute -top-0.5 -end-0.5 min-w-[15px] h-[15px] px-1 bg-cyan-500 text-black text-[10px] font-bold rounded-full flex items-center justify-center">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* البحث — ظاهر دائماً، لا يحتاج فتح الفلاتر */}
      <div className="px-3 py-2 border-b border-rasad-border">
        <label htmlFor="rsd-search" className="sr-only">{t('news.search')}</label>
        <div className="relative">
          <Search className="absolute top-1/2 -translate-y-1/2 start-2 w-4 h-4 text-slate-400" aria-hidden="true" />
          <input
            id="rsd-search"
            type="search"
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder={t('news.searchPlaceholder')}
            maxLength={100}
            className="w-full bg-rasad-bg border border-rasad-border rounded-lg ps-8 pe-8 py-1.5 text-sm text-slate-100 placeholder:text-slate-400 focus-ring"
          />
          {searchDraft && (
            <button
              onClick={() => setSearchDraft('')}
              aria-label={t('news.clearSearch')}
              className="absolute top-1/2 -translate-y-1/2 end-2 text-slate-400 hover:text-white focus-ring rounded"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* الفلاتر */}
      {showFilters && (
        <div className="px-3 py-2 border-b border-rasad-border bg-rasad-bg space-y-2">
          <div className="flex flex-wrap gap-1">
            <button onClick={() => onFilterChange?.('category', '')}
              className={`text-xs px-2 py-1 rounded focus-ring ${!filters?.category ? 'bg-cyan-400/20 text-cyan-200' : 'bg-rasad-border text-slate-300'}`}>
              {t('news.all')}
            </button>
            {Object.entries(CATEGORIES).map(([key, cat]) => (
              <button key={key} onClick={() => onFilterChange?.('category', filters?.category === key ? '' : key)}
                aria-pressed={filters?.category === key}
                className={`text-xs px-2 py-1 rounded focus-ring ${filters?.category === key ? 'text-white' : 'bg-rasad-border text-slate-300'}`}
                style={filters?.category === key ? { background: cat.color + '30', color: cat.color } : {}}>
                {cat.icon} {t(`categories.${key}`)}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-1">
            {Object.entries(SEVERITIES).map(([key, sev]) => (
              <button key={key} onClick={() => onFilterChange?.('severity', filters?.severity === key ? '' : key)}
                aria-pressed={filters?.severity === key}
                className={`text-xs px-2 py-1 rounded focus-ring ${filters?.severity === key ? 'text-white' : 'bg-rasad-border text-slate-300'}`}
                style={filters?.severity === key ? { background: sev.color + '30', color: sev.color } : {}}>
                {sev.dot} {t(`severity.${key}`)}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="rsd-country" className="block text-xs text-slate-300 mb-1">{t('news.country')}</label>
              <select
                id="rsd-country"
                value={filters?.country_code || ''}
                onChange={(e) => onFilterChange?.('country_code', e.target.value)}
                className="w-full bg-rasad-panel border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
              >
                <option value="">{t('news.allCountries')}</option>
                {Object.entries(COUNTRIES).map(([code, info]) => (
                  <option key={code} value={code}>{info.flag} {t(`countries.${code}`)}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="rsd-source" className="block text-xs text-slate-300 mb-1">{t('news.source')}</label>
              <select
                id="rsd-source"
                value={filters?.source || ''}
                onChange={(e) => onFilterChange?.('source', e.target.value)}
                className="w-full bg-rasad-panel border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
              >
                <option value="">{t('news.allSources')}</option>
                {SOURCES.map(src => <option key={src} value={src}>{src}</option>)}
              </select>
            </div>

            <div>
              <label htmlFor="rsd-hours" className="block text-xs text-slate-300 mb-1">{t('news.period')}</label>
              <select
                id="rsd-hours"
                value={filters?.hours || 24}
                onChange={(e) => onFilterChange?.('hours', Number(e.target.value))}
                className="w-full bg-rasad-panel border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
              >
                {TIME_WINDOWS.map(h => (
                  <option key={h} value={h}>{t('time.hoursShort', { count: h })}</option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => { setSearchDraft(''); onResetFilters?.(); }}
                className="w-full flex items-center justify-center gap-1 px-2 py-1 rounded border border-rasad-border text-xs text-slate-300 hover:text-white hover:border-slate-500 focus-ring"
              >
                <RotateCcw className="w-3 h-3" aria-hidden="true" /> {t('news.resetFilters')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* قائمة الأحداث */}
      <div className="flex-1 overflow-y-auto">
        {error ? (
          <div className="flex items-center justify-center h-32 px-4 text-sm text-red-200 text-center" role="alert">
            {t('news.loadFailed')}
          </div>
        ) : loading && events.length === 0 ? (
          <div className="p-3 space-y-2" aria-busy="true" aria-label={t('common.loading')}>
            {[0, 1, 2, 3, 4].map(i => (
              <div key={i} className="shimmer h-16 rounded-lg" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-sm text-slate-300">{t('news.noEvents')}</div>
        ) : (
          events.map(event => {
            const cat = categoryOf(event.category);
            const sev = severityOf(event.severity);
            const flag = COUNTRIES[event.country_code]?.flag || '';
            const isExpanded = expandedId === event.id;
            const link = safeUrl(event.url);

            return (
              <div
                key={event.id}
                role="button"
                tabIndex={0}
                aria-expanded={isExpanded}
                className={`border-b border-rasad-border/50 px-3 py-2 cursor-pointer transition-colors hover:bg-rasad-border/30 focus-ring ${isExpanded ? 'bg-rasad-border/20' : ''}`}
                onClick={() => { setExpandedId(isExpanded ? null : event.id); onSelectEvent?.(event); }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpandedId(isExpanded ? null : event.id); onSelectEvent?.(event); } }}
              >
                {/* الشريط العلوي */}
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-xs" aria-hidden="true">{cat.icon}</span>
                  <span className="text-[11px] px-1.5 py-0.5 rounded" style={{ background: cat.color + '20', color: cat.color }}>
                    {t(`categories.${event.category}`, { defaultValue: t('categories.general') })}
                  </span>
                  <span className="text-[11px] px-1.5 py-0.5 rounded" style={{ background: sev.color + '20', color: sev.color }}>
                    {t(`severity.${event.severity}`, { defaultValue: t('severity.low') })}
                  </span>
                  <span className="flex-1" />
                  <span className="text-[11px] text-slate-300">{timeAgo(event.event_date, t)}</span>
                </div>

                {/* العنوان */}
                <h4 className="text-sm font-semibold text-slate-100 leading-relaxed mb-1 line-clamp-2">{event.title}</h4>

                {/* التفاصيل */}
                <div className="flex items-center gap-2 text-[11px] text-slate-300">
                  {flag && <span>{flag} {t(`countries.${event.country_code}`, { defaultValue: event.country || '' })}</span>}
                  {/* bdi يعزل اسم المصدر اللاتيني فلا تقفز النقطة في سياق RTL */}
                  <span>• <bdi>{event.source}</bdi></span>
                </div>

                {/* التوسع */}
                {isExpanded && (
                  <div className="mt-2 pt-2 border-t border-rasad-border/50">
                    {event.description && (
                      <p className="text-xs text-slate-300 leading-relaxed mb-2">{event.description}</p>
                    )}
                    {link && (
                      <a href={link} target="_blank" rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 text-xs text-cyan-300 hover:underline focus-ring rounded">
                        <ExternalLink className="w-3 h-3" aria-hidden="true" /> {t('news.sourceLink')}
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
