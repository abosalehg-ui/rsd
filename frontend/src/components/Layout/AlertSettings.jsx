/**
 * رصد - قائمة إعدادات التنبيهات الصوتية + قائمة التنبيهات الأخيرة
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, BellOff, Volume2, X, Check, Trash2 } from 'lucide-react';

const SEVERITY_VALUES = [
  { value: 'low',      color: '#64748b' },
  { value: 'medium',   color: '#3b82f6' },
  { value: 'high',     color: '#f59e0b' },
  { value: 'critical', color: '#ef4444' },
];

const CATEGORY_VALUES = ['military', 'nuclear', 'diplomatic', 'humanitarian', 'economic'];

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `قبل ${Math.floor(diff)} ث`;
  if (diff < 3600) return `قبل ${Math.floor(diff / 60)} د`;
  return `قبل ${Math.floor(diff / 3600)} س`;
}

export default function AlertSettings({
  isOpen,
  onClose,
  prefs,
  setPrefs,
  recentAlerts,
  clearRecent,
  testSound,
  requestDesktopPermission,
  onSelectAlert,
}) {
  const { t, i18n } = useTranslation();
  const [permResult, setPermResult] = useState(null);
  const isAr = i18n.language === 'ar';

  if (!isOpen) return null;

  const toggleCategory = (cat) => {
    setPrefs(prev => {
      const has = prev.categories.includes(cat);
      return { ...prev, categories: has ? prev.categories.filter(c => c !== cat) : [...prev.categories, cat] };
    });
  };

  const handleEnableDesktop = async () => {
    const granted = await requestDesktopPermission();
    setPermResult(granted ? 'granted' : 'denied');
    if (granted) setPrefs({ desktopNotifications: true });
  };

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-start justify-center pt-16 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md mx-4 bg-[#0d1117] border border-[#1e293b] rounded-xl shadow-2xl text-slate-200 font-arabic"
        dir={isAr ? 'rtl' : 'ltr'}
      >
        {/* الرأس */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e293b]">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-cyan-400">{t('alerts.title')}</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-[#1e293b] rounded text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* تفعيل/تعطيل */}
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{t('alerts.sound')}</div>
              <div className="text-xs text-slate-500">{t('alerts.soundDesc')}</div>
            </div>
            <button
              dir="ltr"
              onClick={() => setPrefs({ enabled: !prefs.enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${prefs.enabled ? 'bg-cyan-500' : 'bg-slate-600'}`}
              aria-pressed={prefs.enabled}
            >
              <span
                className="inline-block h-4 w-4 rounded-full bg-white transition-transform"
                style={{ transform: `translateX(${prefs.enabled ? '24px' : '4px'})` }}
              />
            </button>
          </div>

          {/* اختبار الصوت */}
          <button
            onClick={testSound}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400 hover:bg-cyan-500/20 text-sm"
          >
            <Volume2 className="w-4 h-4" />
            {t('alerts.testSound')}
          </button>

          {/* عتبة الخطورة */}
          <div>
            <div className="text-sm font-medium mb-2">{t('alerts.threshold')}</div>
            <div className="grid grid-cols-2 gap-2">
              {SEVERITY_VALUES.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setPrefs({ threshold: opt.value })}
                  className={`px-3 py-2 rounded-lg text-xs border transition-colors ${
                    prefs.threshold === opt.value
                      ? 'bg-cyan-500/10 border-cyan-500 text-white'
                      : 'bg-[#111827] border-[#1e293b] text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <span className="inline-block w-2 h-2 rounded-full mx-2" style={{ background: opt.color }} />
                  {t(`severity.${opt.value}`)}
                </button>
              ))}
            </div>
          </div>

          {/* التصنيفات */}
          <div>
            <div className="text-sm font-medium mb-2">
              {t('alerts.categories')}
              <span className="text-xs text-slate-500 mx-2">
                {prefs.categories.length === 0 ? t('alerts.categoriesAll') : t('alerts.categoriesSelected', { count: prefs.categories.length })}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORY_VALUES.map(value => {
                const selected = prefs.categories.includes(value);
                return (
                  <button
                    key={value}
                    onClick={() => toggleCategory(value)}
                    className={`px-3 py-2 rounded-lg text-xs border transition-colors flex items-center justify-between ${
                      selected
                        ? 'bg-cyan-500/10 border-cyan-500 text-white'
                        : 'bg-[#111827] border-[#1e293b] text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <span>{t(`categories.${value}`)}</span>
                    {selected && <Check className="w-3 h-3 text-cyan-400" />}
                  </button>
                );
              })}
            </div>
            {prefs.categories.length > 0 && (
              <button
                onClick={() => setPrefs({ categories: [] })}
                className="text-[10px] text-slate-500 hover:text-cyan-400 mt-2"
              >
                {t('alerts.clearSelection')}
              </button>
            )}
          </div>

          {/* فاصل التكرار */}
          <div>
            <div className="text-sm font-medium mb-2 flex justify-between">
              <span>{t('alerts.throttle')}</span>
              <span className="font-mono text-cyan-400">{prefs.throttleSeconds}s</span>
            </div>
            <input
              type="range"
              min="5"
              max="120"
              step="5"
              value={prefs.throttleSeconds}
              onChange={(e) => setPrefs({ throttleSeconds: Number(e.target.value) })}
              className="w-full accent-cyan-500"
            />
            <div className="text-[10px] text-slate-500 mt-1">{t('alerts.throttleDesc')}</div>
          </div>

          {/* إشعارات سطح المكتب */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="text-sm font-medium">{t('alerts.desktop')}</div>
              <span className={`text-[10px] px-2 py-0.5 rounded ${prefs.desktopNotifications ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
                {prefs.desktopNotifications ? t('alerts.desktopEnabled') : t('alerts.desktopDisabled')}
              </span>
            </div>
            <button
              onClick={handleEnableDesktop}
              className="w-full px-3 py-2 text-xs bg-[#111827] border border-[#1e293b] rounded-lg text-slate-300 hover:border-cyan-500 hover:text-cyan-400"
            >
              {prefs.desktopNotifications ? t('alerts.desktopReask') : t('alerts.desktopRequest')}
            </button>
            {permResult === 'denied' && (
              <div className="text-[10px] text-red-400 mt-1">{t('alerts.desktopDenied')}</div>
            )}
          </div>

          {/* التنبيهات الأخيرة */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium">{t('alerts.recent')}</div>
              {recentAlerts.length > 0 && (
                <button
                  onClick={clearRecent}
                  className="text-[10px] text-slate-500 hover:text-red-400 flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" /> {t('alerts.clear')}
                </button>
              )}
            </div>
            {recentAlerts.length === 0 ? (
              <div className="text-xs text-slate-500 italic text-center py-3 bg-[#0a0e17] rounded">{t('alerts.recentEmpty')}</div>
            ) : (
              <div className="space-y-2">
                {recentAlerts.map((a, i) => (
                  <button
                    key={i}
                    onClick={() => { onSelectAlert?.(a); onClose(); }}
                    className="w-full text-right p-2 bg-[#0a0e17] hover:bg-[#111827] border border-[#1e293b] rounded text-xs"
                  >
                    <div className="text-slate-200 line-clamp-2 leading-relaxed">{a.title}</div>
                    <div className="flex justify-between mt-1 text-[10px] text-slate-500">
                      <span>{a.country || ''}</span>
                      <span>{timeAgo(a._alertedAt)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
