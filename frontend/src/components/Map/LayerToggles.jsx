/**
 * رصد - لوحة تبديل الطبقات (مشتركة).
 *
 * كانت مفاتيح الطبقات داخل RasadMap فقط، فيفقدها وضع الكرة 3D بالكامل. هذا
 * المكوّن المستقل يُعرض فوق الكرة في App كي يتكافأ الوضعان.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Layers } from 'lucide-react';

const TOGGLES = [
  ['events', 'map.events', 'accent-cyan-400'],
  ['flights', 'map.flights', 'accent-purple-400'],
  ['iran', 'map.iran', 'accent-red-400', '🇮🇷'],
  ['nuclear', 'map.nuclear', 'accent-yellow-400', '☢️'],
  ['bases', 'map.bases', 'accent-violet-400', '⚔️'],
  ['pipelines', 'map.pipelines', 'accent-amber-400', '🛢️'],
];

export default function LayerToggles({ layers = {}, onLayerChange, className = '' }) {
  const { t } = useTranslation();
  return (
    <fieldset className={`bg-rasad-panel/95 border border-rasad-border rounded-lg p-3 text-sm ${className}`}>
      <legend className="sr-only">{t('map.layers')}</legend>
      <div className="flex items-center gap-2 mb-2">
        <Layers className="w-4 h-4 text-slate-300" aria-hidden="true" />
        <span className="text-slate-200 font-medium">{t('map.layers')}</span>
      </div>
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
  );
}
