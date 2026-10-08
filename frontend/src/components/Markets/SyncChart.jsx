/**
 * رصد - مخطط التزامن: مؤشر الخطر النووي ومؤشر الأثر على المملكة مقابل برنت.
 *
 * محور زمني واحد ولوحتان متراصّتان لا محوران رأسيان على رسم واحد: المؤشران
 * على تدريج 0-100 مشترك في الأعلى، وبرنت بدولاراته في الأسفل. محوران رأسيان
 * يوحيان بتقاطعات لا معنى لها (يكفي تغيير التدريج لصنع «تزامن»)، واللوحتان
 * تُبقيان المقارنة في الزمن وحده — وهي كل ما يقوله المخطط.
 *
 * فجوات المؤشرين (أيام قبل أقدم حدث محفوظ) تبقى فجوات لا أصفارًا، وبرنت يصل
 * فوق العطل لأنها أيام بلا تداول لا قيم مفقودة. مؤشر خط عمودي يتبع المؤشر
 * ويعرض قيم اليوم الثلاث، وكذلك الأسهم بلوحة المفاتيح؛ وجدول البيانات تحته
 * لمن لا يستعمل المؤشر.
 *
 * `dir="ltr"`: الزمن يجري من اليسار لليمين في اللغتين.
 */
import React, { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SYNC_COLORS, THEME } from '../../utils/constants';
import { formatObservedDate, formatQuote } from '../../utils/markets';

const W = 360;
const LEFT = 26;
const RIGHT = 30;
const A_TOP = 8;
const A_BOTTOM = 112;
const B_TOP = 128;
const B_BOTTOM = 188;
const AXIS_Y = 202;
const H = 208;
const PLOT_W = W - LEFT - RIGHT;

/** مسار SVG يقطع الخط عند القيم الفارغة (`connect=false`) أو يصلها. */
export function linePath(values, x, y, { connect = false } = {}) {
  let d = '';
  let pen = false;
  values.forEach((v, i) => {
    if (v == null) {
      if (!connect) pen = false;
      return;
    }
    d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

function lastIndex(values) {
  for (let i = values.length - 1; i >= 0; i -= 1) if (values[i] != null) return i;
  return -1;
}

export default function SyncChart({ points = [] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const svgRef = useRef(null);
  const [hover, setHover] = useState(null);

  const geo = useMemo(() => {
    const n = points.length;
    const x = (i) => LEFT + (n > 1 ? (i * PLOT_W) / (n - 1) : PLOT_W / 2);
    const yA = (v) => A_BOTTOM - (Math.max(0, Math.min(100, v)) / 100) * (A_BOTTOM - A_TOP);
    const brent = points.map(p => p.brent);
    const known = brent.filter(v => v != null);
    let lo = known.length ? Math.min(...known) : 0;
    let hi = known.length ? Math.max(...known) : 1;
    if (hi - lo < 1) { lo -= 0.5; hi += 0.5; }
    const pad = (hi - lo) * 0.08;
    lo -= pad; hi += pad;
    const yB = (v) => B_BOTTOM - ((v - lo) / (hi - lo)) * (B_BOTTOM - B_TOP);
    const nuclear = points.map(p => p.nuclear);
    const ksa = points.map(p => p.ksa);
    return { n, x, yA, yB, lo, hi, brent, nuclear, ksa, hasBrent: known.length > 0 };
  }, [points]);

  if (!points.length) return null;

  const pick = (clientX) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || !rect.width) return;
    const vx = ((clientX - rect.left) / rect.width) * W;
    const i = Math.round(((vx - LEFT) / PLOT_W) * (geo.n - 1));
    setHover(Math.max(0, Math.min(geo.n - 1, i)));
  };

  const onKeyDown = (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    const step = e.key === 'ArrowRight' ? 1 : -1;
    setHover(h => Math.max(0, Math.min(geo.n - 1, (h ?? geo.n - 1) + (h == null ? 0 : step))));
  };

  const series = [
    { key: 'nuclear', values: geo.nuclear, y: geo.yA, color: SYNC_COLORS.nuclear },
    { key: 'ksa', values: geo.ksa, y: geo.yA, color: SYNC_COLORS.ksa },
  ];
  const dateLabel = (i) => formatObservedDate(points[i]?.date, lang, { day: 'numeric', month: 'short' });
  const tickIdx = [0, Math.floor((geo.n - 1) / 2), geo.n - 1].filter((v, i, a) => a.indexOf(v) === i);
  const hp = hover != null ? points[hover] : null;

  return (
    <figure className="m-0">
      {/* المفتاح: خطوط قصيرة تطابق العلامات، والهوية مكتوبة لا لونًا وحده */}
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-2xs text-slate-300 mb-1.5" aria-label={t('markets.sync.legend')}>
        {['nuclear', 'ksa', 'brent'].map(k => (
          <li key={k} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3.5 h-0.5 rounded" style={{ background: SYNC_COLORS[k] }} aria-hidden="true" />
            {t(`markets.sync.series.${k}`)}
          </li>
        ))}
      </ul>

      <div className="relative" dir="ltr">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="w-full h-auto block touch-none focus-ring rounded"
          role="img"
          aria-label={t('markets.sync.chartLabel', { days: geo.n })}
          tabIndex={0}
          onPointerMove={(e) => pick(e.clientX)}
          onPointerDown={(e) => pick(e.clientX)}
          onPointerLeave={() => setHover(null)}
          onKeyDown={onKeyDown}
          onBlur={() => setHover(null)}
        >
          {/* شبكة باهتة للوحة المؤشرين */}
          {[0, 50, 100].map(v => (
            <g key={v}>
              <line x1={LEFT} x2={W - RIGHT} y1={geo.yA(v)} y2={geo.yA(v)} stroke={THEME.border} strokeWidth="1" />
              <text x={LEFT - 4} y={geo.yA(v) + 3} textAnchor="end" fontSize="8" fill={THEME.textMuted}>{v}</text>
            </g>
          ))}
          {/* لوحة برنت: حدّاها الأدنى والأعلى في النافذة */}
          <line x1={LEFT} x2={W - RIGHT} y1={B_BOTTOM} y2={B_BOTTOM} stroke={THEME.border} strokeWidth="1" />
          {geo.hasBrent && (
            <>
              <text x={LEFT - 4} y={B_TOP + 6} textAnchor="end" fontSize="8" fill={THEME.textMuted}>{Math.round(geo.hi)}</text>
              <text x={LEFT - 4} y={B_BOTTOM} textAnchor="end" fontSize="8" fill={THEME.textMuted}>{Math.round(geo.lo)}</text>
            </>
          )}
          {!geo.hasBrent && (
            <text x={LEFT + PLOT_W / 2} y={(B_TOP + B_BOTTOM) / 2} textAnchor="middle" fontSize="9" fill={THEME.textMuted}>
              {t('markets.sync.noBrent')}
            </text>
          )}

          {series.map(s => {
            const li = lastIndex(s.values);
            return (
              <g key={s.key}>
                <path d={linePath(s.values, geo.x, s.y)} fill="none" stroke={s.color} strokeWidth="2"
                  strokeLinejoin="round" strokeLinecap="round" data-testid={`sync-line-${s.key}`} />
                {li >= 0 && (
                  <text x={W - RIGHT + 3} y={s.y(s.values[li]) + 3} fontSize="8" fill={THEME.textSecondary}>
                    {s.values[li].toFixed(0)}
                  </text>
                )}
              </g>
            );
          })}
          {geo.hasBrent && (
            <g>
              <path d={linePath(geo.brent, geo.x, geo.yB, { connect: true })} fill="none" stroke={SYNC_COLORS.brent}
                strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" data-testid="sync-line-brent" />
              {(() => {
                const li = lastIndex(geo.brent);
                return (
                  <text x={W - RIGHT + 3} y={geo.yB(geo.brent[li]) + 3} fontSize="8" fill={THEME.textSecondary}>
                    {geo.brent[li].toFixed(0)}
                  </text>
                );
              })()}
            </g>
          )}

          {tickIdx.map(i => (
            <text key={i} x={geo.x(i)} y={AXIS_Y} fontSize="8" fill={THEME.textMuted}
              textAnchor={i === 0 ? 'start' : i === geo.n - 1 ? 'end' : 'middle'}>
              {dateLabel(i)}
            </text>
          ))}

          {hover != null && (
            <g pointerEvents="none">
              <line x1={geo.x(hover)} x2={geo.x(hover)} y1={A_TOP} y2={B_BOTTOM} stroke={THEME.textSecondary} strokeWidth="1" opacity="0.6" />
              {series.map(s => s.values[hover] != null && (
                <circle key={s.key} cx={geo.x(hover)} cy={s.y(s.values[hover])} r="3.5" fill={s.color} stroke={THEME.panel} strokeWidth="2" />
              ))}
              {geo.brent[hover] != null && (
                <circle cx={geo.x(hover)} cy={geo.yB(geo.brent[hover])} r="3.5" fill={SYNC_COLORS.brent} stroke={THEME.panel} strokeWidth="2" />
              )}
            </g>
          )}
        </svg>

        {hp && (
          <div
            role="status"
            className="pointer-events-none absolute top-0 z-10 rounded border border-rasad-border bg-rasad-bg/95 px-2 py-1.5 text-2xs shadow-lg"
            style={hover > geo.n / 2
              ? { right: `${100 - (geo.x(hover) / W) * 100 + 2}%` }
              : { left: `${(geo.x(hover) / W) * 100 + 2}%` }}
            dir={lang === 'ar' ? 'rtl' : 'ltr'}
          >
            <div className="text-slate-400">
              {formatObservedDate(hp.date, lang)}{hp.partial ? ` · ${t('markets.sync.partial')}` : ''}
            </div>
            {[
              ['nuclear', hp.nuclear == null ? null : hp.nuclear.toFixed(1), t('markets.sync.noCoverage')],
              ['ksa', hp.ksa == null ? null : hp.ksa.toFixed(1), t('markets.sync.noCoverage')],
              ['brent', hp.brent == null ? null : `$${formatQuote(hp.brent)}`, t('markets.sync.noTrading')],
            ].map(([k, v, missing]) => (
              <div key={k} className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-0.5 rounded" style={{ background: SYNC_COLORS[k] }} aria-hidden="true" />
                {v == null
                  ? <span className="text-slate-300">{missing}</span>
                  : <span className="font-mono font-semibold text-slate-100" dir="ltr">{v}</span>}
                <span className="text-slate-400">{t(`markets.sync.series.${k}`)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <details className="mt-2">
        <summary className="cursor-pointer text-2xs text-cyan-300 hover:text-cyan-200 focus-ring rounded w-fit">
          {t('markets.sync.tableToggle')}
        </summary>
        <div className="mt-1 max-h-48 overflow-y-auto">
          <table className="w-full text-2xs">
            <caption className="sr-only">{t('markets.sync.tableCaption')}</caption>
            <thead>
              <tr className="text-slate-400">
                <th scope="col" className="text-start font-normal py-0.5">{t('markets.sync.date')}</th>
                <th scope="col" className="text-end font-normal">{t('markets.sync.series.nuclear')}</th>
                <th scope="col" className="text-end font-normal">{t('markets.sync.series.ksa')}</th>
                <th scope="col" className="text-end font-normal">{t('markets.sync.series.brent')}</th>
              </tr>
            </thead>
            <tbody>
              {[...points].reverse().map(p => (
                <tr key={p.date} className="border-b border-rasad-border/50 text-slate-200">
                  <th scope="row" className="text-start font-normal py-0.5">{formatObservedDate(p.date, lang)}</th>
                  <td dir="ltr" className="text-end font-mono">{p.nuclear == null ? '—' : p.nuclear.toFixed(1)}</td>
                  <td dir="ltr" className="text-end font-mono">{p.ksa == null ? '—' : p.ksa.toFixed(1)}</td>
                  <td dir="ltr" className="text-end font-mono">{p.brent == null ? '—' : formatQuote(p.brent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
