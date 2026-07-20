/**
 * رصد - الشريط العلوي مع أخبار عاجلة
 */
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Satellite, Radio, Wifi, WifiOff, RefreshCw, Bell, BellOff, Globe2, Map as MapIcon, Box } from 'lucide-react';

export default function Header({ stats, isConnected, onRefresh, refreshing, alertsEnabled = true, lastAlertEvent = null, recentAlertCount = 0, onOpenAlerts, viewMode = '2d', onToggleView }) {
  const { t, i18n } = useTranslation();
  const isAr = i18n.language === 'ar';
  const localeCode = isAr ? 'ar-SA' : 'en-US';
  const [currentTime, setCurrentTime] = useState(new Date());
  const [lastFetch, setLastFetch] = useState(new Date());
  const [bellShake, setBellShake] = useState(false);
  const lastAlertIdRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // اهتزاز الجرس عند ورود تنبيه جديد
  useEffect(() => {
    if (!lastAlertEvent) return;
    if (lastAlertIdRef.current === lastAlertEvent.id) return;
    lastAlertIdRef.current = lastAlertEvent.id;
    setBellShake(true);
    const t = setTimeout(() => setBellShake(false), 1800);
    return () => clearTimeout(t);
  }, [lastAlertEvent]);

  // تحديث وقت آخر فحص عند تغير stats
  useEffect(() => {
    if (stats) {
      setLastFetch(new Date());
    }
  }, [stats]);

  const timeStr = currentTime.toLocaleTimeString(localeCode, {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });
  const dateStr = currentTime.toLocaleDateString(localeCode, {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  const lastFetchStr = lastFetch.toLocaleTimeString(localeCode, {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });

  const toggleLang = () => i18n.changeLanguage(isAr ? 'en' : 'ar');

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
              {t('app.name')} <span className="text-sm text-slate-500 font-mono">RSD</span>
            </h1>
            <p className="text-[10px] text-slate-500 -mt-0.5">{t('app.tagline')}</p>
          </div>
        </div>

        {/* الإحصائيات السريعة */}
        <div className="flex items-center gap-6">
          {/* مؤشر التصعيد */}
          {stats && (
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#111827] border border-[#1e293b]">
                <span className="text-slate-400">{t('app.events')}</span>
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
                <span>{t('app.escalation')}</span>
                <span className="font-bold font-mono">{stats.escalation_index || 0}%</span>
              </div>
            </div>
          )}
        </div>

        {/* التوقيت والحالة */}
        <div className="flex items-center gap-4">
          {/* مؤشر آخر فحص */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#111827] border border-[#1e293b]">
            <span className="text-[10px] text-slate-500">{t('app.lastCheck')}</span>
            <span className="text-[10px] text-cyan-400 font-mono">{lastFetchStr}</span>
          </div>

          {/* زر تبديل الخريطة 2D/3D */}
          {onToggleView && (
            <button
              onClick={onToggleView}
              className="flex items-center gap-1 px-2 py-1 rounded bg-[#111827] border border-[#1e293b] hover:border-cyan-500 text-cyan-400 transition-colors"
              title={viewMode === '3d' ? t('map.view2d') : t('map.view3d')}
              aria-label={viewMode === '3d' ? t('map.view2d') : t('map.view3d')}
            >
              {viewMode === '3d' ? <MapIcon className="w-3.5 h-3.5" /> : <Box className="w-3.5 h-3.5" />}
              <span className="text-[10px] font-medium">{viewMode === '3d' ? t('map.view2d') : t('map.view3d')}</span>
            </button>
          )}

          {/* زر تبديل اللغة */}
          <button
            onClick={toggleLang}
            className="flex items-center gap-1 px-2 py-1 rounded bg-[#111827] border border-[#1e293b] hover:border-cyan-500 text-cyan-400 transition-colors"
            title={t('lang.switch')}
            aria-label={t('lang.switch')}
          >
            <Globe2 className="w-3.5 h-3.5" />
            <span className="text-[10px] font-medium font-mono">{isAr ? 'EN' : 'ع'}</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={refreshing}
            className={`p-1.5 rounded hover:bg-[#1e293b] transition-colors ${
              refreshing ? 'text-cyan-400 animate-spin' : 'text-slate-400 hover:text-cyan-400'
            }`}
            title={refreshing ? t('app.refreshing') : t('app.refresh')}
            aria-label={refreshing ? t('app.refreshing') : t('app.refresh')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* جرس التنبيهات */}
          <button
            onClick={onOpenAlerts}
            className={`relative p-1.5 rounded hover:bg-[#1e293b] transition-colors ${
              alertsEnabled ? 'text-cyan-400' : 'text-slate-500'
            }`}
            title={t('alerts.settings')}
            aria-label={t('alerts.settings')}
          >
            {alertsEnabled
              ? <Bell className={`w-4 h-4 ${bellShake ? 'bell-alert' : ''}`} />
              : <BellOff className="w-4 h-4" />}
            {recentAlertCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                {recentAlertCount > 9 ? '9+' : recentAlertCount}
              </span>
            )}
          </button>

          <div className={`flex items-center gap-1.5 text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
            {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            <span>{isConnected ? t('app.connected') : t('app.disconnected')}</span>
          </div>

          <div className={isAr ? 'text-left' : 'text-right'}>
            <div className="text-sm font-mono text-cyan-400 font-bold">{timeStr}</div>
            <div className="text-[10px] text-slate-500">{dateStr}</div>
          </div>
        </div>
      </div>
    </header>
  );
}