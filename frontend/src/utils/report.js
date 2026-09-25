/**
 * رصد - تصدير تقرير الرصد النووي والإشعاعي (Markdown و HTML مستقل).
 *
 * دوال نقيّة تأخذ بيانات `/api/nuclear/brief` ودالة الترجمة وتعيد نصًّا،
 * فتُختبر وحدها. HTML المصدَّر ملف واحد بلا سكربتات ولا موارد خارجية — يُفتح
 * دون اتصال ويُرفق في بريد كما هو. كل قيمة من المصادر تمرّ عبر esc().
 */
import { esc, safeUrl } from './security';
import { ksaPlace } from './constants';

const LEVEL_COLORS = { low: '#2f8a5f', medium: '#a8860f', high: '#c2610f', critical: '#c4262b' };

function trendText(delta, t) {
  const d = Number(delta) || 0;
  if (Math.abs(d) < 0.5) return t('trend.flat');
  return t(d > 0 ? 'trend.up' : 'trend.down', { value: Math.abs(d).toFixed(1) });
}

export function summaryLine(brief, t) {
  const r = brief.risk || {};
  return t('report.summaryLine', {
    index: (r.index ?? 0).toFixed(1),
    level: t(`risk.levels.${r.level || 'low'}`),
    trend: trendText(r.delta, t),
    stories: r.stories ?? 0,
    events: brief.totals?.events ?? 0,
    near: r.near_ksa_stories ?? 0,
  });
}

const SECTIONS = ['top', 'nearKsa', 'incidents', 'political'];
const SECTION_KEYS = { top: 'top_stories', nearKsa: 'near_ksa', incidents: 'incidents', political: 'political' };

function storyMeta(s, t) {
  const parts = [
    s.topic ? t(`topics.${s.topic}`) : '',
    s.country_code ? t(`countries.${s.country_code}`, { defaultValue: s.country || s.country_code }) : '',
    s.source_name || s.source,
    s.story_source_count > 1 ? t('events.sources', { count: s.story_source_count }) : '',
  ];
  return parts.filter(Boolean).join(' · ');
}

export function formatDate(iso, lang) {
  if (!iso) return '';
  return new Intl.DateTimeFormat(lang === 'ar' ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB', {
    dateStyle: 'long', timeStyle: 'short',
  }).format(new Date(iso));
}

export function toMarkdown(brief, t, lang = 'ar') {
  const lines = [
    `# ${t('report.title')}`,
    '',
    `${t(`report.periods.${brief.period_hours}`, { defaultValue: `${brief.period_hours}h` })} — ${t('report.generated', { date: formatDate(brief.generated_at, lang) })}`,
    '',
    `## ${t('report.sections.summary')}`,
    '',
    summaryLine(brief, t),
    '',
  ];

  SECTIONS.forEach(key => {
    const items = brief[SECTION_KEYS[key]] || [];
    lines.push(`## ${t(`report.sections.${key}`)}`, '');
    if (!items.length) lines.push(`_${t('report.none')}_`, '');
    items.forEach(s => {
      const link = safeUrl(s.url);
      const title = link ? `[${s.title}](${link})` : s.title;
      lines.push(`- **${Math.round(s.risk_score ?? 0)}** — ${title}  `, `  ${storyMeta(s, t)}`);
    });
    lines.push('');
  });

  lines.push(`## ${t('report.sections.facilities')}`, '');
  if (!(brief.facilities || []).length) lines.push(`_${t('report.none')}_`);
  (brief.facilities || []).forEach(f => {
    const name = lang === 'ar' ? f.name_ar : f.name_en;
    const dist = f.distance_to_ksa_km != null
      ? ` — ${t('facilities.distance', { km: Math.round(f.distance_to_ksa_km), place: ksaPlace(f, lang) })}` : '';
    lines.push(`- ${name}: ${t('facilities.stories', { count: f.stories })}, ${t('risk.score')} ${Math.round(f.max_risk)}${dist}`);
  });
  lines.push('', `## ${t('report.sections.sources')}`, '');
  Object.entries(brief.sources || {}).forEach(([name, n]) => lines.push(`- ${name}: ${n}`));
  lines.push('', `## ${t('report.sections.method')}`, '', t('report.method'), '');
  return lines.join('\n');
}

function htmlStories(items, t) {
  if (!items.length) return `<p class="none">${esc(t('report.none'))}</p>`;
  return `<ol>${items.map(s => {
    const link = safeUrl(s.url);
    const level = s.risk_score >= 75 ? 'critical' : s.risk_score >= 55 ? 'high' : s.risk_score >= 30 ? 'medium' : 'low';
    const title = link ? `<a href="${esc(link)}">${esc(s.title)}</a>` : esc(s.title);
    return `<li><span class="score" style="color:${LEVEL_COLORS[level]}">${esc(Math.round(s.risk_score ?? 0))}</span>
      <div><div class="t">${title}</div><div class="m">${esc(storyMeta(s, t))}</div></div></li>`;
  }).join('')}</ol>`;
}

export function toHtml(brief, t, lang = 'ar') {
  const dir = lang === 'ar' ? 'rtl' : 'ltr';
  const r = brief.risk || {};
  const color = LEVEL_COLORS[r.level] || LEVEL_COLORS.low;
  const sections = SECTIONS.map(key => `
    <section><h2>${esc(t(`report.sections.${key}`))}</h2>${htmlStories(brief[SECTION_KEYS[key]] || [], t)}</section>`).join('');
  const facilities = (brief.facilities || []).map(f => `<tr><td>${esc(lang === 'ar' ? f.name_ar : f.name_en)}</td>
      <td>${esc(t('facilities.stories', { count: f.stories }))}</td><td>${esc(Math.round(f.max_risk))}</td>
      <td>${f.distance_to_ksa_km != null ? esc(t('facilities.distance', { km: Math.round(f.distance_to_ksa_km), place: ksaPlace(f, lang) })) : ''}</td></tr>`).join('');
  const sources = Object.entries(brief.sources || {}).map(([n, c]) => `<li>${esc(n)}: ${esc(c)}</li>`).join('');

  return `<!doctype html>
<html lang="${lang}" dir="${dir}"><head><meta charset="utf-8">
<title>${esc(t('report.title'))}</title>
<style>
  body{font-family:"IBM Plex Sans Arabic",Tahoma,sans-serif;color:#15191e;max-width:820px;margin:32px auto;padding:0 20px;line-height:1.6}
  h1{font-size:22px;margin:0}h2{font-size:15px;margin:28px 0 8px;border-bottom:1px solid #d6dbe0;padding-bottom:4px}
  .meta{color:#5b6670;font-size:13px}.index{display:flex;align-items:baseline;gap:10px;margin:18px 0 6px}
  .index b{font-size:40px;font-family:"IBM Plex Mono",monospace;color:${color}}.index span{color:${color};font-weight:600}
  ol{list-style:none;padding:0;margin:0}li{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #eef0f2}
  .score{font-family:"IBM Plex Mono",monospace;font-weight:700;min-width:28px}.t{font-weight:600}.m{color:#5b6670;font-size:12px}
  a{color:#0b5e8a;text-decoration:none}table{border-collapse:collapse;width:100%;font-size:13px}
  td{padding:6px 4px;border-bottom:1px solid #eef0f2}.none{color:#8a949c;font-style:italic}.method{font-size:12px;color:#5b6670}
</style></head><body>
<h1>${esc(t('report.title'))}</h1>
<div class="meta">${esc(t(`report.periods.${brief.period_hours}`, { defaultValue: `${brief.period_hours}h` }))} — ${esc(t('report.generated', { date: formatDate(brief.generated_at, lang) }))}</div>
<div class="index"><b>${esc((r.index ?? 0).toFixed(1))}</b><span>${esc(t(`risk.levels.${r.level || 'low'}`))}</span></div>
<p>${esc(summaryLine(brief, t))}</p>
${sections}
<section><h2>${esc(t('report.sections.facilities'))}</h2>${facilities ? `<table>${facilities}</table>` : `<p class="none">${esc(t('report.none'))}</p>`}</section>
<section><h2>${esc(t('report.sections.sources'))}</h2><ul>${sources}</ul></section>
<section><h2>${esc(t('report.sections.method'))}</h2><p class="method">${esc(t('report.method'))}</p></section>
</body></html>`;
}

/** تنزيل نصّ كملف (Blob) — لا خادم ولا إذن. */
export function downloadText(filename, text, type) {
  const blob = new Blob([text], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
