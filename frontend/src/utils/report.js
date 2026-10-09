/**
 * رصد - تصدير تقرير الرصد النووي والإشعاعي (Markdown و HTML مستقل)، والموجز
 * السردي في رأسه.
 *
 * دوال نقيّة تأخذ بيانات `/api/nuclear/brief` ودالة الترجمة وتعيد نصًّا،
 * فتُختبر وحدها. HTML المصدَّر ملف واحد بلا سكربتات ولا موارد خارجية — يُفتح
 * دون اتصال ويُرفق في بريد كما هو. كل قيمة من المصادر تمرّ عبر esc().
 *
 * الموجز السردي **قوالب نصية** (`report.narrative.*`) تُملأ ببيانات الفترة، لا
 * صياغة مولَّدة. يُبنى جملًا من «مقاطع»: نص، أو استشهاد بحدث (`E<id>`). العرض
 * في التطبيق يجعل الاستشهاد رابطًا يفتح الحدث، والتصدير يكتبه نصًّا ويسرد
 * روابط المصادر في قائمة مراجع — فتبقى صياغة واحدة للمكانين.
 */
import { esc, safeUrl } from './security';
import { ksaPlace, localeFor, riskLevel } from './constants';
import { pct } from './chains';

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

// ===== الموجز السردي =====

const TITLE_MAX = 90;
const CHAIN_TITLE_MAX = 60;
const MARK = '\u0000';

export function shortTitle(title, max = TITLE_MAX) {
  const s = String(title || '').trim();
  return s.length > max ? `${s.slice(0, max - 1).trimEnd()}…` : s;
}

const fmt1 = (v) => (Number(v) || 0).toFixed(1);
const text = (value) => ({ type: 'text', text: value });

/** يملأ قالب ترجمة؛ المعامل المصفوفة يُدرج مقاطع (استشهادات) مكانه. */
function fill(t, key, params = {}) {
  const segs = {};
  const plain = {};
  Object.entries(params).forEach(([k, v]) => {
    if (Array.isArray(v)) {
      segs[k] = v;
      plain[k] = `${MARK}${k}${MARK}`;
    } else plain[k] = v;
  });
  const out = [];
  t(key, plain).split(new RegExp(`${MARK}(\\w+)${MARK}`)).forEach((part, i) => {
    if (i % 2) out.push(...(segs[part] || []));
    else if (part) out.push(text(part));
  });
  return out;
}

function joinSegs(groups, sep) {
  return groups.flatMap((g, i) => (i ? [text(sep), ...g] : g));
}

// العنوان مقطع مستقل («title») كي يُعزل اتجاهه: عنوان إنجليزي داخل فقرة عربية
// يتبعثر بلا عزل (<bdi> في التطبيق وHTML)
function storyItem(t, s, max = TITLE_MAX) {
  return [
    ...fill(t, 'report.narrative.quote', { title: [{ type: 'title', text: shortTitle(s.title, max) }] }),
    text(' ('),
    { type: 'cite', id: s.id, url: s.url, title: s.title },
    text(')'),
  ];
}

function narrativeTrend(delta, t, trend) {
  const d = Number(delta) || 0;
  const dir = trend || (Math.abs(d) < 0.5 ? 'flat' : d > 0 ? 'up' : 'down');
  if (dir === 'flat') return t('report.narrative.trendFlat');
  return t(dir === 'up' ? 'report.narrative.trendUp' : 'report.narrative.trendDown', { value: fmt1(Math.abs(d)) });
}

function chainItem(t, chain) {
  const nodes = chain.nodes.map(n => storyItem(t, n, CHAIN_TITLE_MAX));
  return [
    ...joinSegs(nodes, ` ${t('chains.arrow')} `),
    text(` ${t('report.narrative.chainConfidence', { value: pct(chain.confidence) })}`),
  ];
}

/**
 * جمل الموجز: المؤشران وتغيّرهما عن الفترة السابقة، وأبرز القصص، والأعلى أثرًا
 * على المملكة، والقطاعات الصاعدة، وأبرز سلاسل الترابط. كل جملة مصفوفة مقاطع.
 */
export function buildNarrative(brief, t) {
  if (!brief) return [];
  const N = (key, params) => fill(t, `report.narrative.${key}`, params);
  const sep = t('report.narrative.sep');
  const out = [];

  const r = brief.risk || {};
  out.push(N('nuclear', {
    index: fmt1(r.index), level: t(`risk.levels.${r.level || 'low'}`),
    trend: narrativeTrend(r.delta, t), prev: fmt1(r.prev_index),
  }));

  const k = brief.ksa_impact;
  // نافذة أطول من نصف مدة الاحتفاظ: الفترة السابقة محذوفة، فالمقارنة بها «صعود» كاذب
  const kComparable = Boolean(k) && k.comparable !== false && k.delta != null;
  if (k) {
    const level = t(`risk.levels.${k.level || 'low'}`);
    out.push(kComparable
      ? N('ksa', { index: fmt1(k.index), level, trend: narrativeTrend(k.delta, t, k.trend), prev: fmt1(k.prev_index) })
      : N('ksaNoCompare', { index: fmt1(k.index), level }));
  }

  const top = (brief.top_stories || []).slice(0, 3);
  out.push(top.length
    ? N('top', { items: joinSegs(top.map(s => storyItem(t, s)), sep) })
    : N('topNone'));

  const seen = new Set(top.map(s => s.id));
  const ksaTop = (k?.top_events || []).filter(e => !seen.has(e.id)).slice(0, 2);
  if (ksaTop.length) out.push(N('ksaTop', { items: joinSegs(ksaTop.map(e => storyItem(t, e)), sep) }));

  if (kComparable) {
    const rising = (k.sectors || [])
      .filter(s => s.trend === 'up' && s.delta > 0)
      .sort((a, b) => b.delta - a.delta)
      .slice(0, 3);
    out.push(rising.length
      ? N('rising', {
        items: rising.map(s => t('report.narrative.sector', { name: t(`impact.sectors.${s.key}`), delta: fmt1(s.delta) })).join(sep),
      })
      : N('risingNone'));
  }

  if (Array.isArray(brief.chains)) {
    const chains = brief.chains.slice(0, 2);
    out.push(chains.length
      ? N('chains', { items: joinSegs(chains.map(c => chainItem(t, c)), t('report.narrative.chainSep')) })
      : N('chainsNone'));
  }
  return out;
}

/**
 * الموجز نصًّا عاديًا: الاستشهاد يُكتب `E<id>`. `escTitle` يهرّب العناوين
 * (نص خارجي من الخلاصات) دون نص القوالب — Markdown يمرّر `mdEsc`.
 */
export function narrativeText(sentences, escTitle = (x) => x) {
  return sentences
    .map(segs => segs.map(s => (s.type === 'cite' ? `E${s.id}` : s.type === 'title' ? escTitle(s.text) : s.text)).join(''))
    .join(' ');
}

/**
 * تهريب نص خارجي (عنوان RSS) داخل Markdown: عنوان فيه `](` يكسر الرابط، و`<…>`
 * يُحقن HTML في العارضات التي تعرض HTML الخام داخل Markdown.
 */
export function mdEsc(value) {
  return String(value ?? '').replace(/[\\`*_[\]()<>]/g, '\\$&');
}

/** رابط داخل `(…)` أو `<…>`: الأقواس والمسافة تُنهيان الرابط مبكرًا فتُشفَّر. */
export function mdUrl(url) {
  return String(url ?? '').replace(/[()<> ]/g, c => `%${c.charCodeAt(0).toString(16).toUpperCase().padStart(2, '0')}`);
}

/** الموجز HTML مُهرَّبًا: العناوين معزولة الاتجاه، والاستشهاد نص `E<id>`. */
export function narrativeHtml(sentences) {
  return sentences
    .map(segs => segs.map(s => {
      if (s.type === 'cite') return `E${esc(s.id)}`;
      if (s.type === 'title') return `<bdi>${esc(s.text)}</bdi>`;
      return esc(s.text);
    }).join(''))
    .join(' ');
}

/** الأحداث المستشهَد بها بترتيب أول ظهور، مع روابطها الآمنة فقط. */
export function narrativeNotes(sentences) {
  const notes = new Map();
  sentences.flat().forEach(s => {
    if (s.type === 'cite' && !notes.has(s.id)) notes.set(s.id, { id: s.id, title: s.title, url: safeUrl(s.url) });
  });
  return [...notes.values()];
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

/** تاريخ تالف من الخادم يُعرض كما هو: format() يرمي RangeError فيُسقط النافذة كلها. */
export function formatDate(iso, lang) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return new Intl.DateTimeFormat(localeFor(lang), { dateStyle: 'long', timeStyle: 'short' }).format(d);
}

export function toMarkdown(brief, t, lang = 'ar') {
  const narrative = buildNarrative(brief, t);
  const notes = narrativeNotes(narrative);
  const lines = [
    `# ${t('report.title')}`,
    '',
    `${t(`report.periods.${brief.period_hours}`, { defaultValue: `${brief.period_hours}h` })} — ${t('report.generated', { date: formatDate(brief.generated_at, lang) })}`,
    '',
    `## ${t('report.narrative.title')}`,
    '',
    narrativeText(narrative, mdEsc),
    '',
    `_${t('report.narrative.template')}_`,
    '',
  ];
  if (notes.length) {
    lines.push(`### ${t('report.narrative.notes')}`, '');
    notes.forEach((n, i) => lines.push(`${i + 1}. **E${n.id}** — ${mdEsc(n.title)}${n.url ? ` — <${mdUrl(n.url)}>` : ''}`));
    lines.push('');
  }
  lines.push(
    `## ${t('report.sections.summary')}`,
    '',
    summaryLine(brief, t),
    '',
  );

  SECTIONS.forEach(key => {
    const items = brief[SECTION_KEYS[key]] || [];
    lines.push(`## ${t(`report.sections.${key}`)}`, '');
    if (!items.length) lines.push(`_${t('report.none')}_`, '');
    items.forEach(s => {
      const link = safeUrl(s.url);
      const title = link ? `[${mdEsc(s.title)}](${mdUrl(link)})` : mdEsc(s.title);
      lines.push(`- **${Math.round(s.risk_score ?? 0)}** — ${title}  `, `  ${mdEsc(storyMeta(s, t))}`);
    });
    lines.push('');
  });

  lines.push(`## ${t('report.sections.facilities')}`, '');
  if (!(brief.facilities || []).length) lines.push(`_${t('report.none')}_`);
  (brief.facilities || []).forEach(f => {
    const name = lang === 'ar' ? f.name_ar : f.name_en;
    const dist = f.distance_to_ksa_km != null
      ? ` — ${t('facilities.distance', { km: Math.round(f.distance_to_ksa_km), place: ksaPlace(f, lang) })}` : '';
    lines.push(`- ${mdEsc(name)}: ${t('facilities.stories', { count: f.stories })}, ${t('risk.score')} ${Math.round(f.max_risk)}${dist}`);
  });
  lines.push('', `## ${t('report.sections.sources')}`, '');
  Object.entries(brief.sources || {}).forEach(([name, n]) => lines.push(`- ${mdEsc(name)}: ${n}`));
  lines.push('', `## ${t('report.sections.method')}`, '', t('report.method'), '');
  return lines.join('\n');
}

function htmlStories(items, t) {
  if (!items.length) return `<p class="none">${esc(t('report.none'))}</p>`;
  return `<ol>${items.map(s => {
    const link = safeUrl(s.url);
    const level = riskLevel(s.risk_score);
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
  const narrative = buildNarrative(brief, t);
  const notes = narrativeNotes(narrative).map(n => `<li><b>E${esc(n.id)}</b> — ${esc(n.title)}${
    n.url ? ` — <a href="${esc(n.url)}">${esc(n.url)}</a>` : ''}</li>`).join('');

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
  .narrative p{margin:6px 0}.notes{list-style:decimal;padding-inline-start:20px;font-size:12px;color:#5b6670}
  .notes li{display:list-item;border:0;padding:2px 0}
</style></head><body>
<h1>${esc(t('report.title'))}</h1>
<div class="meta">${esc(t(`report.periods.${brief.period_hours}`, { defaultValue: `${brief.period_hours}h` }))} — ${esc(t('report.generated', { date: formatDate(brief.generated_at, lang) }))}</div>
<section class="narrative"><h2>${esc(t('report.narrative.title'))}</h2><p>${narrativeHtml(narrative)}</p>
<p class="method">${esc(t('report.narrative.template'))}</p>
${notes ? `<h3 class="method">${esc(t('report.narrative.notes'))}</h3><ol class="notes">${notes}</ol>` : ''}</section>
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
