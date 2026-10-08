/**
 * رصد - أجزاء عرض رابط «سبب ← أثر»: شارة الثقة، وأدلّة الرابط (العلاقة،
 * والقاعدة التي أنتجته، والكيانات المشتركة، والفارق الزمني، والمعادلة).
 *
 * كل رابط يُعرض بقاعدته وأرقامه — بروح شرح الدرجة النووية: الرابط فرضية قاعدية
 * للتحقق، لا حكم سببي.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { confidenceColor, confidenceFormula, confidenceLevel, entityName, pct, relationText } from '../../utils/chains';

export function ConfidenceBadge({ value, className = '' }) {
  const { t } = useTranslation();
  const color = confidenceColor(value);
  const label = `${t('chains.confidenceTitle')}: ${pct(value)} — ${t(`chains.levels.${confidenceLevel(value)}`)}`;
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded px-1.5 py-0.5 font-mono text-2xs font-semibold tabular-nums ${className}`}
      style={{ color, background: `${color}1f`, boxShadow: `inset 0 0 0 1px ${color}55` }}
      title={label}
      aria-label={label}
    >
      {pct(value)}
    </span>
  );
}

/** معرّف القاعدة التي أنتجت الرابط (اسمها في التلميح) — العلاقة نفسها تُعرض فوقه. */
export function RuleLabel({ ruleId }) {
  const { t } = useTranslation();
  return (
    <span className="text-2xs text-slate-400" title={t(`chains.rules.${ruleId}`, { defaultValue: ruleId })}>
      {t('chains.rule')}: <code dir="ltr" className="font-mono text-slate-400">{ruleId}</code>
    </span>
  );
}

/** العلاقة + القاعدة + الكيانات المشتركة + الفارق الزمني + المعادلة. */
export function LinkEvidence({ link }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'ar' ? 'ar' : 'en';
  const ev = link.evidence || {};
  const shared = ev.shared || [];
  return (
    <div className="mt-1 space-y-0.5 text-2xs leading-relaxed">
      <p className="text-slate-300">{relationText(link, lang)}</p>
      <p><RuleLabel ruleId={link.rule_id} /></p>
      {shared.length > 0 && (
        <p className="text-slate-400">
          {t('chains.shared')}:{' '}
          {shared.map((e, i) => (
            <span key={`${e.kind}:${e.key}`}>
              {i > 0 && t('chains.sep')}
              <span className="text-slate-300">{entityName(e, lang)}</span>
              <span className="text-slate-500"> ({t(`chains.kinds.${e.kind}`, { defaultValue: e.kind })})</span>
            </span>
          ))}
          {ev.hours != null && <> · {t('chains.gap', { hours: ev.hours })}</>}
        </p>
      )}
      {ev.components && (
        <p className="text-slate-500" title={t('chains.formulaHelp')}>
          {t('chains.formulaLabel')}: <span dir="ltr" className="font-mono tabular-nums">{confidenceFormula(link)}</span>
        </p>
      )}
    </div>
  );
}
