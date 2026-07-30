/**
 * رصد - لوحة تبديل الطبقات (مشتركة بين الخريطة 2D والكرة 3D).
 *
 * منسدلة: زر رأس يفتح/يطوي قائمة المفاتيح بدل أن تشغل اللوحة مساحة الخريطة
 * طوال الوقت، مع حفظ الحالة كي تبقى بين الجلسات.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Layers, ChevronDown } from 'lucide-react';

const TOGGLES = [
  ['events', 'map.events', 'accent-cyan-400'],
  ['flights', 'map.flights', 'accent-purple-400'],
  ['iran', 'map.iran', 'accent-red-400', '🇮🇷'],
  ['nuclear', 'map.nuclear', 'accent-yellow-400', '☢️'],
  ['bases', 'map.bases', 'accent-violet-400', '⚔️'],
  ['pipelines', 'map.pipelines', 'accent-amber-400', '🛢️'],
];

const OPEN_KEY = 'rsd-layers-open';

export default function LayerToggles({ layers = {}, onLayerChange, className = '' }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(OPEN_KEY) === '1'; } catch { return false; }
  });

  const toggleOpen = () => setOpen(prev => {
    const next = !prev;
    try { localStorage.setItem(OPEN_KEY, next ? '1' : '0'); } catch { /* التخزين معطّل */ }
    return next;
  });

  const activeCount = TOGGLES.filter(([key]) => layers[key]).length;

  return (
    <div className={`bg-rasad-panel/95 border border-rasad-border rounded-lg text-sm ${className}`}>
      <button
        type="button"
        onClick={toggleOpen}
        aria-expanded={open}
        aria-label={open ? t('map.hideLayers') : t('map.showLayers')}
        title={open ? t('map.hideLayers') : t('map.showLayers')}
        className="flex items-center gap-2 w-full px-3 py-2.5 focus-ring rounded-lg hover:bg-rasad-border/50"
      >
        <Layers className="w-4 h-4 text-slate-300" aria-hidden="true" />
        <span className="text-slate-200 font-medium">{t('map.layers')}</span>
        <span className="text-[11px] font-mono text-cyan-300 bg-cyan-400/10 border border-cyan-400/20 rounded-full px-1.5">
          {activeCount}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-slate-300 ms-auto transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>
      {open && (
        <fieldset className="px-3 pb-3 pt-1">
          <legend className="sr-only">{t('map.layers')}</legend>
          {TOGGLES.map(([key, labelKey, accent, emoji]) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer mb-1">
              {/* أسماء أصناف Tailwind كاملة صراحةً كي لا يحذفها فحص المحتوى الثابت */}
              <input
                type="checkbox"
                checked={Boolean(layers[key])}
                onChange={e => onLayerChange?.(key, e.target.checked)}
                className={`w-4 h-4 ${accent} focus-ring`}
              />
              <span className="text-slate-200">{emoji ? `${emoji} ` : ''}{t(labelKey)}</span>
            </label>
          ))}
        </fieldset>
      )}
    </div>
  );
}
