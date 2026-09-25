/**
 * رصد - عرض التقرير الدوري للرصد النووي والإشعاعي.
 *
 * نافذة بملء الشاشة بتصميم ورقة: تُقرأ على الشاشة، وتُطبع (أو تُحفظ PDF من
 * نافذة الطباعة) بأنماط @media print في index.css، أو تُنزَّل HTML/Markdown.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Printer, FileCode, FileText } from 'lucide-react';
import { usePolling } from '../../hooks/usePolling';
import { getNuclearBrief } from '../../utils/api';
import { SEVERITIES, ksaPlace, riskLevel } from '../../utils/constants';
import { downloadText, formatDate, summaryLine, toHtml, toMarkdown } from '../../utils/report';
import { safeUrl } from '../../utils/security';

const PERIODS = [24, 72, 168];
const SECTIONS = [
  ['top', 'top_stories'], ['nearKsa', 'near_ksa'], ['incidents', 'incidents'], ['political', 'political'],
];

function StoryRows({ items }) {
  const { t } = useTranslation();
  if (!items?.length) return <p className="text-sm text-slate-400 print-muted">{t('report.none')}</p>;
  return (
    <ol className="divide-y divide-rasad-border/60">
      {items.map(s => {
        const color = SEVERITIES[riskLevel(s.risk_score)].color;
        const link = safeUrl(s.url);
        return (
          <li key={s.id} className="flex gap-3 py-2.5">
            <span className="font-mono text-sm font-semibold tabular-nums w-8 shrink-0" style={{ color }}>
              {Math.round(s.risk_score ?? 0)}
            </span>
            <div className="min-w-0">
              {link ? (
                <a href={link} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-slate-100 hover:text-cyan-200 focus-ring rounded">
                  {s.title}
                </a>
              ) : <span className="text-sm font-semibold text-slate-100">{s.title}</span>}
              <div className="text-xs text-slate-400 print-muted">
                {[s.topic && t(`topics.${s.topic}`),
                  s.country_code && t(`countries.${s.country_code}`, { defaultValue: s.country || s.country_code }),
                  s.source_name,
                  s.story_source_count > 1 && t('events.sources', { count: s.story_source_count }),
                ].filter(Boolean).join(' · ')}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default function ReportView({ open, onClose }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'ar' ? 'ar' : 'en';
  const [hours, setHours] = useState(24);
  const closeRef = useRef(null);

  const { data: brief, error, loading } = usePolling(
    useCallback(() => (open ? getNuclearBrief(hours) : Promise.resolve(null)), [open, hours]),
    300000, [open, hours],
  );

  useEffect(() => {
    if (!open) return undefined;
    const prev = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); prev?.focus?.(); };
  }, [open, onClose]);

  if (!open) return null;

  const stamp = new Date().toISOString().slice(0, 10);
  const r = brief?.risk;
  const color = r ? SEVERITIES[r.level || 'low'].color : undefined;

  return (
    // items-start: بدونه تمطّ flex الورقة إلى ارتفاع الشاشة فقط، فيتجاوز المحتوى
    // الطويل خلفيتها ويظهر النص فوق الخريطة مباشرة.
    <div className="fixed inset-0 z-[10000] bg-black/70 flex items-start justify-center overflow-y-auto print-root" role="dialog" aria-modal="true" aria-labelledby="report-title">
      <div className="w-full max-w-3xl my-0 sm:my-6 min-h-full sm:min-h-0 bg-rasad-panel sm:rounded-xl border border-rasad-border shadow-2xl print-card">
        <div className="no-print sticky top-0 z-10 flex flex-wrap items-center gap-2 px-4 py-3 bg-rasad-panel/95 backdrop-blur border-b border-rasad-border sm:rounded-t-xl">
          <label htmlFor="report-period" className="text-xs text-slate-400">{t('report.period')}</label>
          <select
            id="report-period" value={hours} onChange={e => setHours(Number(e.target.value))}
            className="bg-rasad-bg border border-rasad-border rounded px-2 py-1 text-xs text-slate-100 focus-ring"
          >
            {PERIODS.map(h => <option key={h} value={h}>{t(`report.periods.${h}`)}</option>)}
          </select>
          <span className="flex-1" />
          <button onClick={() => window.print()} disabled={!brief}
            className="min-h-9 inline-flex items-center gap-1.5 px-3 rounded-md bg-rasad-raised border border-rasad-border text-xs text-slate-100 hover:border-cyan-500 disabled:opacity-50 focus-ring">
            <Printer className="w-4 h-4" aria-hidden="true" /> {t('report.print')}
          </button>
          <button onClick={() => downloadText(`rasad-nuclear-${stamp}.html`, toHtml(brief, t, lang), 'text/html')} disabled={!brief}
            className="min-h-9 inline-flex items-center gap-1.5 px-3 rounded-md bg-rasad-raised border border-rasad-border text-xs text-slate-100 hover:border-cyan-500 disabled:opacity-50 focus-ring">
            <FileCode className="w-4 h-4" aria-hidden="true" /> {t('report.html')}
          </button>
          <button onClick={() => downloadText(`rasad-nuclear-${stamp}.md`, toMarkdown(brief, t, lang), 'text/markdown')} disabled={!brief}
            className="min-h-9 inline-flex items-center gap-1.5 px-3 rounded-md bg-rasad-raised border border-rasad-border text-xs text-slate-100 hover:border-cyan-500 disabled:opacity-50 focus-ring">
            <FileText className="w-4 h-4" aria-hidden="true" /> {t('report.markdown')}
          </button>
          <button ref={closeRef} onClick={onClose} aria-label={t('report.close')}
            className="min-w-9 min-h-9 flex items-center justify-center rounded-md text-slate-300 hover:text-white hover:bg-rasad-border focus-ring">
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <article className="px-6 sm:px-10 py-8">
          <header>
            <p className="text-xs font-semibold tracking-wide text-hazard">{t('app.name')} · {t('app.tagline')}</p>
            <h1 id="report-title" className="mt-1 text-2xl font-semibold text-slate-50">{t('report.title')}</h1>
            {brief && (
              <p className="mt-1 text-xs text-slate-400 print-muted">
                {t(`report.periods.${brief.period_hours}`)} — {t('report.generated', { date: formatDate(brief.generated_at, lang) })}
              </p>
            )}
          </header>

          {error && !brief ? (
            <p className="mt-8 text-sm text-red-200" role="alert">{t('report.failed')}</p>
          ) : !brief ? (
            <p className="mt-8 text-sm text-slate-300" aria-busy={loading}>{t('report.loading')}</p>
          ) : (
            <>
              <section className="mt-6">
                <h2 className="sr-only">{t('report.sections.summary')}</h2>
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-5xl font-semibold tabular-nums" style={{ color }}>{(r.index ?? 0).toFixed(1)}</span>
                  <span className="text-lg font-semibold" style={{ color }}>{t(`risk.levels.${r.level || 'low'}`)}</span>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-200">{summaryLine(brief, t)}</p>
              </section>

              {SECTIONS.map(([key, field]) => (
                <section key={key} className="mt-8">
                  <h2 className="text-sm font-semibold text-slate-100 border-b border-rasad-border pb-1.5">{t(`report.sections.${key}`)}</h2>
                  <StoryRows items={brief[field]} />
                </section>
              ))}

              <section className="mt-8">
                <h2 className="text-sm font-semibold text-slate-100 border-b border-rasad-border pb-1.5">{t('report.sections.facilities')}</h2>
                {brief.facilities?.length ? (
                  <table className="mt-2 w-full text-sm">
                    <tbody>
                      {brief.facilities.map(f => (
                        <tr key={f.facility_id} className="border-b border-rasad-border/60">
                          <td className="py-2 text-slate-100">{lang === 'ar' ? f.name_ar : f.name_en}</td>
                          <td className="py-2 text-slate-400 print-muted">{t('facilities.stories', { count: f.stories })}</td>
                          <td className="py-2 font-mono tabular-nums" style={{ color: SEVERITIES[riskLevel(f.max_risk)].color }}>{Math.round(f.max_risk)}</td>
                          <td className="py-2 text-xs text-slate-400 print-muted">
                            {f.distance_to_ksa_km != null && t('facilities.distance', { km: Math.round(f.distance_to_ksa_km), place: ksaPlace(f, lang) })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <p className="mt-2 text-sm text-slate-400">{t('report.none')}</p>}
              </section>

              <section className="mt-8">
                <h2 className="text-sm font-semibold text-slate-100 border-b border-rasad-border pb-1.5">{t('report.sections.sources')}</h2>
                <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-300 print-muted">
                  {Object.entries(brief.sources || {}).map(([n, c]) => (
                    <li key={n}><bdi>{n}</bdi> <span className="font-mono text-slate-500">{c}</span></li>
                  ))}
                </ul>
              </section>

              <section className="mt-8">
                <h2 className="text-sm font-semibold text-slate-100 border-b border-rasad-border pb-1.5">{t('report.sections.method')}</h2>
                <p className="mt-2 text-xs leading-relaxed text-slate-400 print-muted">{t('report.method')}</p>
              </section>
            </>
          )}
        </article>
      </div>
    </div>
  );
}
