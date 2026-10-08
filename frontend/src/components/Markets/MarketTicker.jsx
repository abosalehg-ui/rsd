/**
 * رصد - شريط الطاقة والأسواق المضغوط في الهيدر.
 *
 * لكل سلسلة: اسمها المختصر، آخر قيمة، ونسبة التغيّر عن القيمة السابقة بلون
 * وسهم (أخضر صعودًا، أحمر هبوطًا — عُرف الأسواق، والسهم يحمل الاتجاه لمن
 * لا يميّز اللون). بعدها **تاريخ البيانات** صراحةً: FRED يومي ويتأخّر يومًا
 * أو أكثر، فلا يُعرض الشريط على أنه لحظي أبدًا.
 *
 * بلا مفتاح وبلا قيم مخزّنة: تلميح «أضف FRED_API_KEY للتفعيل» بدل الاختفاء.
 * القيم تأتي من قاعدة الخادم، فآخر المعروف يبقى ظاهرًا دون اتصال.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUpRight, ArrowDownRight, Minus, Fuel, KeyRound } from 'lucide-react';
import { MARKET_SERIES } from '../../utils/constants';
import { CHANGE_CLASS, direction, formatObservedDate, formatPct, formatQuote } from '../../utils/markets';

const ARROWS = { up: ArrowUpRight, down: ArrowDownRight, flat: Minus };

export function ChangeBadge({ pct, className = '' }) {
  const { t } = useTranslation();
  const dir = direction(pct);
  if (pct == null) return null;
  const Icon = ARROWS[dir];
  return (
    <span className={`inline-flex items-center font-mono tabular-nums ${CHANGE_CLASS[dir]} ${className}`} dir="ltr">
      <Icon className="w-3 h-3" aria-hidden="true" />
      {formatPct(pct)}
      <span className="sr-only">{t(`markets.dir.${dir}`)}</span>
    </span>
  );
}

export default function MarketTicker({ markets, onOpen, className = '' }) {
  const { t, i18n } = useTranslation();
  if (!markets) return null;

  let content;
  if (!markets.has_data && markets.enabled) {
    // مفعّل ولم تصل أول دفعة بعد
    content = (
      <>
        <Fuel className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />
        <span className="text-slate-400">{t('markets.pending')}</span>
      </>
    );
  } else if (!markets.has_data) {
    content = (
      <>
        <KeyRound className="w-3.5 h-3.5 text-hazard-soft shrink-0" aria-hidden="true" />
        <span className="text-slate-300">{t('markets.title')}:</span>
        <span className="text-hazard-soft">{t('markets.noKeyShort')}</span>
      </>
    );
  } else {
    const bySeries = Object.fromEntries((markets.series || []).map(s => [s.code, s]));
    const items = MARKET_SERIES.map(code => bySeries[code]).filter(s => s && s.value != null);
    content = (
      <>
        <span className="sr-only">{t('markets.tickerLabel')}</span>
        <Fuel className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />
        {items.map(s => (
          <span key={s.code} className="inline-flex items-center gap-1" data-testid={`ticker-${s.code}`}>
            <span className="text-slate-400">{t(`markets.short.${s.code}`)}</span>
            <span className="font-mono tabular-nums text-slate-100" dir="ltr">{formatQuote(s.value)}</span>
            <ChangeBadge pct={s.change_pct} />
          </span>
        ))}
        <span className="text-slate-500" title={t('markets.lagNote')}>
          {t('markets.asOf', { date: formatObservedDate(markets.as_of, i18n.language, { day: 'numeric', month: 'short' }) })}
        </span>
        {!markets.enabled && <span className="text-hazard-soft">· {t('markets.noKeyShort')}</span>}
      </>
    );
  }

  // الحاوية تمرّر أفقيًا على الشاشات الضيقة؛ الزر نفسه لا يصلح حاوية تمرير
  // (المتصفحات تتجاهل overflow على <button>) فيفيض على عرض الصفحة. و`relative`
  // كي تبقى عناصر sr-only (موضعها مطلق) داخل حاوية القص.
  const inner = 'inline-flex items-center gap-3 whitespace-nowrap text-2xs';
  return (
    <div className={`relative min-w-0 overflow-x-auto ${className}`}>
      {onOpen ? (
        <button
          type="button"
          onClick={onOpen}
          title={t('markets.openPanel')}
          className={`${inner} rounded focus-ring hover:bg-rasad-panel/60 px-1`}
        >
          {content}
        </button>
      ) : (
        <div className={inner}>{content}</div>
      )}
    </div>
  );
}
