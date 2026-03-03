/**
 * رصد - الخط الزمني التفاعلي
 */
import React, { useState, useMemo } from 'react';
import { CATEGORIES, SEVERITIES, timeAgo } from '../../utils/constants';
import { Clock, ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

export default function Timeline({ events = [], onSelectEvent }) {
  const [hoursBack, setHoursBack] = useState(24);
  const [selectedCategory, setSelectedCategory] = useState('');

  const filtered = useMemo(() => {
    let list = [...events].sort((a, b) => new Date(b.event_date) - new Date(a.event_date));
    if (selectedCategory) list = list.filter(e => e.category === selectedCategory);
    return list;
  }, [events, selectedCategory]);

  // تجميع حسب الساعة
  const grouped = useMemo(() => {
    const groups = {};
    filtered.forEach(ev => {
      const d = new Date(ev.event_date);
      const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:00`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(ev);
    });
    return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]));
  }, [filtered]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e293b]">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-bold">الخط الزمني</span>
        </div>
        <div className="flex items-center gap-1">
          {[6, 12, 24, 48].map(h => (
            <button key={h} onClick={() => setHoursBack(h)}
              className={`text-[9px] px-1.5 py-0.5 rounded ${hoursBack === h ? 'bg-cyan-400/20 text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}>
              {h}س
            </button>
          ))}
        </div>
      </div>

      {/* فلتر التصنيف */}
      <div className="flex gap-1 px-3 py-1.5 border-b border-[#1e293b]/50 overflow-x-auto">
        <button onClick={() => setSelectedCategory('')}
          className={`text-[9px] px-1.5 py-0.5 rounded whitespace-nowrap ${!selectedCategory ? 'bg-cyan-400/20 text-cyan-400' : 'text-slate-500'}`}>
          الكل
        </button>
        {Object.entries(CATEGORIES).map(([k, c]) => (
          <button key={k} onClick={() => setSelectedCategory(k)}
            className={`text-[9px] px-1.5 py-0.5 rounded whitespace-nowrap ${selectedCategory === k ? 'text-white' : 'text-slate-500'}`}
            style={selectedCategory === k ? { background: c.color + '20', color: c.color } : {}}>
            {c.icon}
          </button>
        ))}
      </div>

      {/* المحتوى */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {grouped.length === 0 ? (
          <div className="text-center text-slate-500 text-sm mt-8">لا توجد أحداث</div>
        ) : (
          grouped.map(([timeKey, items]) => (
            <div key={timeKey} className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-3 h-3 text-slate-500" />
                <span className="text-[10px] font-mono text-slate-400">{timeKey}</span>
                <span className="text-[9px] bg-[#1e293b] text-slate-500 px-1.5 rounded">{items.length}</span>
                <div className="flex-1 h-px bg-[#1e293b]" />
              </div>
              <div className="space-y-1 mr-4 border-r border-[#1e293b] pr-3">
                {items.map(ev => {
                  const cat = CATEGORIES[ev.category] || CATEGORIES.general;
                  const sev = SEVERITIES[ev.severity] || SEVERITIES.low;
                  return (
                    <div key={ev.id}
                      className="relative flex items-start gap-2 py-1 cursor-pointer hover:bg-[#1e293b]/20 rounded px-1 -mr-1"
                      onClick={() => onSelectEvent?.(ev)}>
                      <div className="absolute -right-[19px] top-2 w-2 h-2 rounded-full border-2 border-[#111827]"
                        style={{ background: cat.color }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1 mb-0.5">
                          <span className="text-[10px]">{cat.icon}</span>
                          <span className="text-[8px] px-1 rounded" style={{ background: sev.color + '15', color: sev.color }}>{sev.dot}</span>
                        </div>
                        <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-2">{ev.title}</p>
                        <span className="text-[9px] text-slate-500">{ev.country} • {ev.source}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
