/**
 * رصد - قائمة إعدادات التنبيهات الصوتية + قائمة التنبيهات الأخيرة
 */
import React, { useState } from 'react';
import { Bell, BellOff, Volume2, X, Check, Trash2 } from 'lucide-react';

const SEVERITY_OPTIONS = [
  { value: 'low',      label: 'منخفض (أي حدث)',         color: '#64748b' },
  { value: 'medium',   label: 'متوسط',                  color: '#3b82f6' },
  { value: 'high',     label: 'مرتفع (موصى به)',        color: '#f59e0b' },
  { value: 'critical', label: 'حرج فقط',                color: '#ef4444' },
];

const CATEGORY_OPTIONS = [
  { value: 'military',     label: '⚔️ عسكري' },
  { value: 'nuclear',      label: '☢️ نووي' },
  { value: 'diplomatic',   label: '🤝 دبلوماسي' },
  { value: 'humanitarian', label: '🆘 إنساني' },
  { value: 'economic',     label: '💰 اقتصادي' },
];

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
  const [permResult, setPermResult] = useState(null);

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
        dir="rtl"
      >
        {/* الرأس */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e293b]">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-cyan-400">إعدادات التنبيهات</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-[#1e293b] rounded text-slate-400 hover:text-white" title="إغلاق">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* تفعيل/تعطيل */}
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">صوت الإنذار</div>
              <div className="text-xs text-slate-500">تشغيل صوت تنبيه عند ورود خبر هام</div>
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
            اختبر الصوت الآن
          </button>

          {/* عتبة الخطورة */}
          <div>
            <div className="text-sm font-medium mb-2">عتبة الخطورة</div>
            <div className="grid grid-cols-2 gap-2">
              {SEVERITY_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setPrefs({ threshold: opt.value })}
                  className={`px-3 py-2 rounded-lg text-xs border transition-colors ${
                    prefs.threshold === opt.value
                      ? 'bg-cyan-500/10 border-cyan-500 text-white'
                      : 'bg-[#111827] border-[#1e293b] text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <span className="inline-block w-2 h-2 rounded-full ml-2" style={{ background: opt.color }} />
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="text-[10px] text-slate-500 mt-2">سيُنبَّه فقط عند ورود أحداث بهذه العتبة أو أعلى منها.</div>
          </div>

          {/* التصنيفات */}
          <div>
            <div className="text-sm font-medium mb-2">
              التصنيفات المهمّة
              <span className="text-xs text-slate-500 mr-2">
                {prefs.categories.length === 0 ? '(الكل)' : `(${prefs.categories.length} محددة)`}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORY_OPTIONS.map(opt => {
                const selected = prefs.categories.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    onClick={() => toggleCategory(opt.value)}
                    className={`px-3 py-2 rounded-lg text-xs border transition-colors flex items-center justify-between ${
                      selected
                        ? 'bg-cyan-500/10 border-cyan-500 text-white'
                        : 'bg-[#111827] border-[#1e293b] text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <span>{opt.label}</span>
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
                مسح التحديد (= الكل)
              </button>
            )}
          </div>

          {/* فاصل التكرار */}
          <div>
            <div className="text-sm font-medium mb-2 flex justify-between">
              <span>فاصل التكرار</span>
              <span className="font-mono text-cyan-400">{prefs.throttleSeconds} ث</span>
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
            <div className="text-[10px] text-slate-500 mt-1">حد أدنى للوقت بين تنبيهين متتاليين</div>
          </div>

          {/* إشعارات سطح المكتب */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="text-sm font-medium">إشعارات سطح المكتب</div>
              <span className={`text-[10px] px-2 py-0.5 rounded ${prefs.desktopNotifications ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
                {prefs.desktopNotifications ? 'مفعّلة' : 'معطّلة'}
              </span>
            </div>
            <button
              onClick={handleEnableDesktop}
              className="w-full px-3 py-2 text-xs bg-[#111827] border border-[#1e293b] rounded-lg text-slate-300 hover:border-cyan-500 hover:text-cyan-400"
            >
              {prefs.desktopNotifications ? 'إعادة طلب الإذن' : 'فعّل إشعارات المتصفح'}
            </button>
            {permResult === 'denied' && (
              <div className="text-[10px] text-red-400 mt-1">المتصفح رفض الإذن. يمكنك تفعيله يدويًا من إعدادات الموقع.</div>
            )}
          </div>

          {/* التنبيهات الأخيرة */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium">آخر التنبيهات</div>
              {recentAlerts.length > 0 && (
                <button
                  onClick={clearRecent}
                  className="text-[10px] text-slate-500 hover:text-red-400 flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" /> مسح
                </button>
              )}
            </div>
            {recentAlerts.length === 0 ? (
              <div className="text-xs text-slate-500 italic text-center py-3 bg-[#0a0e17] rounded">لا توجد تنبيهات حتى الآن</div>
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
