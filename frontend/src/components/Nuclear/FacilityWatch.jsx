/**
 * رصد - المنشآت التي ورد ذكرها بالاسم في الأخبار، الأعلى خطرًا أولًا، مع
 * المسافة إلى أقرب نقطة سعودية (الأثر العابر للحدود هو ما يهمّ الرصد الوطني).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Radiation } from 'lucide-react';
import { COUNTRIES, ksaPlace, riskColor } from '../../utils/constants';

export default function FacilityWatch({ facilities = [], onSelect, limit = 6 }) {
  const { t, i18n } = useTranslation();
  const isAr = i18n.language === 'ar';

  return (
    <section aria-labelledby="facility-watch-title">
      <h2 id="facility-watch-title" className="flex items-center gap-2 px-4 pt-4 pb-2 text-xs font-semibold text-slate-300">
        <Radiation className="w-3.5 h-3.5 text-hazard" aria-hidden="true" />
        {t('facilities.title')}
      </h2>
      {facilities.length === 0 ? (
        <p className="px-4 pb-3 text-xs text-slate-400">{t('facilities.empty')}</p>
      ) : (
        <ul className="px-2 pb-2">
          {facilities.slice(0, limit).map(f => {
            const color = riskColor(f.max_risk);
            return (
              <li key={f.facility_id}>
                <button
                  onClick={() => onSelect?.(f)}
                  className="w-full grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-0.5 rounded-md px-2 py-2 text-start hover:bg-rasad-raised focus-ring"
                >
                  <span className="text-sm text-slate-100 truncate">
                    <span aria-hidden="true">{COUNTRIES[f.country_code]?.flag} </span>
                    {isAr ? f.name_ar : f.name_en}
                  </span>
                  <span className="font-mono text-xs font-semibold tabular-nums" style={{ color }}>
                    {Math.round(f.max_risk)}
                  </span>
                  <span className="text-xs text-slate-400 truncate">
                    {f.distance_to_ksa_km != null && (
                      <span className="font-mono tabular-nums">
                        {t('facilities.distance', { km: Math.round(f.distance_to_ksa_km), place: ksaPlace(f, i18n.language) })}
                      </span>
                    )}
                  </span>
                  <span className="text-xs text-slate-400">{t('facilities.stories', { count: f.stories })}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
