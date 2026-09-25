/**
 * رصد - الشريط العلوي.
 *
 * كان سبع شارات صغيرة متساوية الوزن (الوقت، الاتصال، الجرس، اللغة، 2D/3D،
 * آخر فحص، التحديث). الآن ثلاث مناطق:
 *   الهوية ← المؤشران (المخاطر النووية/الإشعاعية أولًا، ثم التصعيد) باتجاههما
 *   ← الأفعال (التقرير، التحديث، التنبيهات، قائمة إعدادات تجمع اللغة والعرض).
 * حالة الاتصال ووقت آخر تحديث نقطة وسطر واحد بدل شارتين.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Radiation, RefreshCw, Bell, BellOff, Settings, Globe2, Box, Map as MapIcon, FileText, Radio,
  ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react';
import { SEVERITIES, escalationColor, riskLevel } from '../../utils/constants';

const ICON_BTN = 'min-w-11 min-h-11 flex items-center justify-center rounded-md transition-colors focus-ring';

function Delta({ value }) {
  const d = Number(value) || 0;
  if (Math.abs(d) < 0.5) return <Minus className="w-3 h-3 text-slate-400" aria-hidden="true" />;
  const Icon = d > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`inline-flex items-center font-mono text-2xs ${d > 0 ? 'text-red-300' : 'text-emerald-300'}`}>
      <Icon className="w-3 h-3" aria-hidden="true" />{Math.abs(d).toFixed(1)}
    </span>
  );
}

function SettingsMenu({ viewMode, onToggleView, onOpenReport }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const isAr = i18n.language === 'ar';

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onKey); };
  }, [open]);

  const item = 'w-full flex items-center gap-2 px-3 py-2.5 text-sm text-slate-200 hover:bg-rasad-raised focus-ring rounded';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={t('app.settings')}
        title={t('app.settings')}
        className={`${ICON_BTN} text-slate-300 hover:text-white hover:bg-rasad-border`}
      >
        <Settings className="w-4 h-4" aria-hidden="true" />
      </button>
      {open && (
        <div className="absolute end-0 top-full mt-1 z-[2000] w-56 rounded-lg border border-rasad-border bg-rasad-panel p-1 shadow-2xl">
          {/* على الشاشات الصغيرة يختفي زر التقرير من الشريط فيظهر هنا */}
          {onOpenReport && (
            <button className={`${item} sm:hidden`} onClick={() => { onOpenReport(); setOpen(false); }}>
              <FileText className="w-4 h-4 text-hazard" aria-hidden="true" />
              <span className="flex-1 text-start">{t('app.report')}</span>
            </button>
          )}
          <button className={item} onClick={() => { i18n.changeLanguage(isAr ? 'en' : 'ar'); setOpen(false); }}>
            <Globe2 className="w-4 h-4 text-slate-400" aria-hidden="true" />
            <span className="flex-1 text-start">{t('app.language')}</span>
            <span className="text-xs text-slate-400">{isAr ? t('lang.en') : t('lang.ar')}</span>
          </button>
          {onToggleView && (
            <button className={item} onClick={() => { onToggleView(); setOpen(false); }}>
              {viewMode === '3d' ? <MapIcon className="w-4 h-4 text-slate-400" aria-hidden="true" /> : <Box className="w-4 h-4 text-slate-400" aria-hidden="true" />}
              <span className="flex-1 text-start">{t('app.view')}</span>
              <span className="text-xs text-slate-400">{viewMode === '3d' ? t('map.view2d') : t('map.view3d')}</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function Header({
  stats, risk, isConnected, onRefresh, refreshing, alertsEnabled = true, lastAlertEvent = null,
  recentAlertCount = 0, onOpenAlerts, viewMode = '2d', onToggleView, lastFetchedAt = null,
  onOpenReport, onOpenNuclear,
}) {
  const { t, i18n } = useTranslation();
  const isAr = i18n.language === 'ar';
  const localeCode = isAr ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB';
  const [now, setNow] = useState(() => new Date());
  const [bellShake, setBellShake] = useState(false);
  const lastAlertIdRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!lastAlertEvent || lastAlertIdRef.current === lastAlertEvent.id) return undefined;
    lastAlertIdRef.current = lastAlertEvent.id;
    setBellShake(true);
    const timer = setTimeout(() => setBellShake(false), 1800);
    return () => clearTimeout(timer);
  }, [lastAlertEvent]);

  const hm = { hour: '2-digit', minute: '2-digit', hour12: false };
  const timeStr = now.toLocaleTimeString(localeCode, { ...hm, second: '2-digit' });
  const dateStr = now.toLocaleDateString(localeCode, { weekday: 'long', day: 'numeric', month: 'long' });
  const lastStr = lastFetchedAt ? lastFetchedAt.toLocaleTimeString(localeCode, hm) : '—';

  const riskValue = risk?.index ?? null;
  const riskLvl = risk?.level || riskLevel(riskValue);
  const riskColor = SEVERITIES[riskLvl].color;
  const esc = stats?.escalation_index ?? null;

  return (
    <header className="bg-rasad-bg border-b border-rasad-border px-3 sm:px-4 py-1.5">
      <div className="flex items-center gap-3">
        {/* الهوية */}
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="relative flex items-center justify-center w-9 h-9 rounded-full border border-hazard/60 bg-hazard-dim shrink-0">
            <Radiation className="w-5 h-5 text-hazard" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h1 className="text-xl font-bold leading-tight text-slate-50">{t('app.name')}</h1>
            <p className="hidden sm:block text-2xs text-hazard-soft leading-tight truncate">{t('app.tagline')}</p>
          </div>
        </div>

        {/* المؤشران */}
        <div className="hidden md:flex items-center gap-2 ms-4">
          {riskValue !== null && (
            <button
              onClick={onOpenNuclear}
              className="flex items-center gap-2.5 rounded-md border border-rasad-border bg-rasad-panel px-3 py-1.5 hover:border-hazard/60 focus-ring"
              title={t('risk.title')}
            >
              <span className="text-xs text-slate-300">{t('risk.short')}</span>
              <span className="font-mono text-base font-semibold tabular-nums" style={{ color: riskColor }}>{riskValue.toFixed(1)}</span>
              <span className="text-xs font-semibold" style={{ color: riskColor }}>{t(`risk.levels.${riskLvl}`)}</span>
              <Delta value={risk?.delta} />
            </button>
          )}
          {esc !== null && (
            <div
              className="hidden lg:flex items-center gap-2 rounded-md border border-rasad-border bg-rasad-panel px-3 py-1.5"
              title={t('app.escalationHelp')}
            >
              <Radio className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
              <span className="text-xs text-slate-300">{t('stats.escalationIndex')}</span>
              <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: escalationColor(esc) }}>{esc}%</span>
              <Delta value={stats?.escalation_delta} />
              <span className="sr-only">{t('app.escalationHelp')}</span>
            </div>
          )}
          {stats && (
            <div className="hidden xl:flex items-center gap-2 rounded-md border border-rasad-border bg-rasad-panel px-3 py-1.5">
              <span className="text-xs text-slate-300">{t('app.events')}</span>
              <span className="font-mono text-sm font-semibold text-slate-100 tabular-nums">{stats.total || 0}</span>
            </div>
          )}
        </div>

        <span className="flex-1" />

        {/* الحالة والوقت */}
        <div className="hidden sm:flex flex-col items-end leading-tight me-1">
          <span className="font-mono text-sm font-semibold text-slate-100 tabular-nums">{timeStr}</span>
          <span className="text-2xs text-slate-400">{dateStr}</span>
        </div>
        <div
          className={`flex items-center gap-1.5 text-2xs ${isConnected ? 'text-slate-300' : 'text-red-300'}`}
          title={isConnected ? t('app.connected') : t('app.disconnected')}
        >
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'}`} aria-hidden="true" />
          <span className="hidden lg:inline">{t('app.lastUpdate')} <span className="font-mono">{lastStr}</span></span>
          <span className="sr-only">{isConnected ? t('app.connected') : t('app.disconnected')}</span>
        </div>

        {/* الأفعال */}
        <div className="flex items-center gap-0.5">
          {onOpenReport && (
            <button
              onClick={onOpenReport}
              className="min-h-11 hidden sm:inline-flex items-center gap-1.5 px-3 rounded-md border border-hazard/40 text-hazard-soft hover:bg-hazard-dim text-sm focus-ring"
            >
              <FileText className="w-4 h-4" aria-hidden="true" />
              {t('app.report')}
            </button>
          )}
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className={`${ICON_BTN} hover:bg-rasad-border ${refreshing ? 'text-cyan-300' : 'text-slate-300 hover:text-white'}`}
            title={refreshing ? t('app.refreshing') : t('app.refresh')}
            aria-label={refreshing ? t('app.refreshing') : t('app.refresh')}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden="true" />
          </button>
          <button
            onClick={onOpenAlerts}
            className={`relative ${ICON_BTN} hover:bg-rasad-border ${alertsEnabled ? 'text-slate-200' : 'text-slate-400'}`}
            title={t('alerts.settings')}
            aria-label={t('alerts.settings')}
          >
            {alertsEnabled
              ? <Bell className={`w-4 h-4 ${bellShake ? 'bell-alert' : ''}`} aria-hidden="true" />
              : <BellOff className="w-4 h-4" aria-hidden="true" />}
            {recentAlertCount > 0 && (
              <span className="absolute top-1.5 end-1.5 min-w-[16px] h-4 px-1 bg-red-500 text-white text-2xs font-bold rounded-full flex items-center justify-center">
                {recentAlertCount > 9 ? '9+' : recentAlertCount}
              </span>
            )}
          </button>
          <SettingsMenu viewMode={viewMode} onToggleView={onToggleView} onOpenReport={onOpenReport} />
        </div>
      </div>
    </header>
  );
}
