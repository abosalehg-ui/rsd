/**
 * رصد - شريط الأخبار العاجلة
 */
import React, { useState } from 'react';
import { CATEGORIES, SEVERITIES, timeAgo, COUNTRIES } from '../../utils/constants';
import { Newspaper, ExternalLink, Filter, ChevronDown } from 'lucide-react';

export default function NewsFeed({ events = [], onSelectEvent, filters, onFilterChange }) {
  const [expandedId, setExpandedId] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  return (
    <div className="flex flex-col h-full">
      {/* العنوان */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e293b]">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-bold text-white">الأحداث</span>
          <span className="text-[10px] font-mono bg-cyan-400/10 text-cyan-400 px-1.5 py-0.5 rounded">{events.length}</span>
        </div>
        <button onClick={() => setShowFilters(!showFilters)} className="p-1 rounded hover:bg-[#1e293b] text-slate-400">
          <Filter className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* الفلاتر */}
      {showFilters && (
        <div className="px-3 py-2 border-b border-[#1e293b] bg-[#0d1117] space-y-2">
          <div className="flex flex-wrap gap-1">
            <button onClick={() => onFilterChange?.('category', '')}
              className={`text-[10px] px-2 py-0.5 rounded ${!filters?.category ? 'bg-cyan-400/20 text-cyan-400' : 'bg-[#1e293b] text-slate-400'}`}>
              الكل
            </button>
            {Object.entries(CATEGORIES).map(([key, cat]) => (
              <button key={key} onClick={() => onFilterChange?.('category', key)}
                className={`text-[10px] px-2 py-0.5 rounded ${filters?.category === key ? `text-white` : 'bg-[#1e293b] text-slate-400'}`}
                style={filters?.category === key ? { background: cat.color + '30', color: cat.color } : {}}>
                {cat.icon} {cat.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(SEVERITIES).map(([key, sev]) => (
              <button key={key} onClick={() => onFilterChange?.('severity', filters?.severity === key ? '' : key)}
                className={`text-[10px] px-2 py-0.5 rounded ${filters?.severity === key ? 'text-white' : 'bg-[#1e293b] text-slate-400'}`}
                style={filters?.severity === key ? { background: sev.color + '30', color: sev.color } : {}}>
                {sev.dot} {sev.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* قائمة الأحداث */}
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-sm text-slate-500">لا توجد أحداث</div>
        ) : (
          events.map(event => {
            const cat = CATEGORIES[event.category] || CATEGORIES.general;
            const sev = SEVERITIES[event.severity] || SEVERITIES.low;
            const flag = COUNTRIES[event.country_code]?.flag || '';
            const isExpanded = expandedId === event.id;

            return (
              <div
                key={event.id}
                className={`border-b border-[#1e293b]/50 px-3 py-2 cursor-pointer transition-colors hover:bg-[#1e293b]/30 ${isExpanded ? 'bg-[#1e293b]/20' : ''}`}
                onClick={() => { setExpandedId(isExpanded ? null : event.id); onSelectEvent?.(event); }}
              >
                {/* الشريط العلوي */}
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-xs">{cat.icon}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: cat.color + '15', color: cat.color }}>{cat.label}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: sev.color + '15', color: sev.color }}>{sev.dot}</span>
                  <span className="flex-1" />
                  <span className="text-[9px] text-slate-500">{timeAgo(event.event_date)}</span>
                </div>

                {/* العنوان */}
                <h4 className="text-xs font-semibold text-slate-200 leading-relaxed mb-1 line-clamp-2">{event.title}</h4>

                {/* التفاصيل */}
                <div className="flex items-center gap-2 text-[9px] text-slate-500">
                  {flag && <span>{flag} {event.country}</span>}
                  <span>• {event.source}</span>
                </div>

                {/* التوسع */}
                {isExpanded && (
                  <div className="mt-2 pt-2 border-t border-[#1e293b]/50">
                    {event.description && (
                      <p className="text-[11px] text-slate-400 leading-relaxed mb-2">{event.description}</p>
                    )}
                    {event.url && (
                      <a href={event.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[10px] text-cyan-400 hover:underline">
                        <ExternalLink className="w-3 h-3" /> المصدر الأصلي
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
