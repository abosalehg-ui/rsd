/**
 * رصد - الشريط العلوي مع أخبار عاجلة
 */
import React, { useState, useEffect } from 'react';
import { Satellite, Radio, Wifi, WifiOff, RefreshCw } from 'lucide-react';

export default function Header({ stats, isConnected, onRefresh, refreshing }) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [lastFetch, setLastFetch] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // تحديث وقت آخر فحص عند تغير stats
  useEffect(() => {
    if (stats) {
      setLastFetch(new Date());
    }
  }, [stats]);

  const timeStr = currentTime.toLocaleTimeString('ar-SA', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });
  const dateStr = currentTime.toLocaleDateString('ar-SA', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  const lastFetchStr = lastFetch.toLocaleTimeString('ar-SA', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });

  return (
    <header className="bg-[#0d1117] border-b border-[#1e293b] px-4 py-2">
      <div className="flex items-center justify-between">
        {/* الشعار */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Satellite className="w-9 h-9 text-cyan-400" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-cyan-400 tracking-wide font-arabic">
              رصد <span className="text-sm text-slate-500 font-mono">RSD</span>
            </h1>
            <p className="text-[10px] text-slate-500 -mt-0.5">OSINT • الشرق الأوسط</p>
          </div>
        </div>

        {/* الإحصائيات السريعة */}
        <div className="flex items-center gap-6">
          {/* مؤشر التصعيد */}
          {stats && (
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#111827] border border-[#1e293b]">
                <span className="text-slate-400">الأحداث:</span>
                <span className="text-white font-bold font-mono">{stats.total || 0}</span>
              </div>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${
                (stats.escalation_index || 0) > 30
                  ? 'bg-red-500/10 border-red-500/30 text-red-400'
                  : (stats.escalation_index || 0) > 15
                  ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
                  : 'bg-green-500/10 border-green-500/30 text-green-400'
              }`}>
                <Radio className="w-3 h-3 animate-pulse" />
                <span>تصعيد:</span>
                <span className="font-bold font-mono">{stats.escalation_index || 0}%</span>
              </div>
            </div>
          )}
        </div>

        {/* التوقيت والحالة */}
        <div className="flex items-center gap-4">
          {/* مؤشر آخر فحص */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#111827] border border-[#1e293b]">
            <span className="text-[10px] text-slate-500">آخر فحص:</span>
            <span className="text-[10px] text-cyan-400 font-mono">{lastFetchStr}</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={refreshing}
            className={`p-1.5 rounded hover:bg-[#1e293b] transition-colors ${
              refreshing ? 'text-cyan-400 animate-spin' : 'text-slate-400 hover:text-cyan-400'
            }`}
            title={refreshing ? 'جاري التحديث...' : 'تحديث من المصادر'}
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <div className={`flex items-center gap-1.5 text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
            {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            <span>{isConnected ? 'متصل' : 'غير متصل'}</span>
          </div>

          <div className="text-left">
            <div className="text-sm font-mono text-cyan-400 font-bold">{timeStr}</div>
            <div className="text-[10px] text-slate-500">{dateStr}</div>
          </div>
        </div>
      </div>
    </header>
  );
}