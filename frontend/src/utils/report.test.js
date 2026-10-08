import { describe, it, expect, beforeAll } from 'vitest';
import i18n from '../i18n';
import { buildNarrative, narrativeNotes, narrativeText, shortTitle, summaryLine, toHtml, toMarkdown } from './report';

const t = (...args) => i18n.t(...args);

const brief = {
  period_hours: 24,
  generated_at: '2026-09-25T12:00:00Z',
  risk: { index: 44.6, level: 'medium', delta: 3.1, stories: 26, near_ksa_stories: 1 },
  totals: { events: 32, stories: 26 },
  top_stories: [
    { id: 1, title: 'Strike <script>alert(1)</script> on Natanz', url: 'https://ok.test/a', risk_score: 79.2, topic: 'military_threat', source_name: 'Reuters', story_source_count: 3 },
    { id: 2, title: 'Bad link', url: 'javascript:alert(1)', risk_score: 20, topic: 'regulatory', source_name: 'X' },
  ],
  near_ksa: [],
  incidents: [],
  political: [],
  facilities: [{ facility_id: 'ir-natanz', name_ar: 'نطنز', name_en: 'Natanz', stories: 1, max_risk: 79.2, distance_to_ksa_km: 663, nearest_ksa_point: 'الجبيل', nearest_ksa_point_en: 'Jubail' }],
  sources: { Reuters: 3 },
};

const narrativeBrief = {
  ...brief,
  risk: { ...brief.risk, prev_index: 41.5 },
  ksa_impact: {
    index: 62.3, level: 'high', prev_index: 50.1, delta: 12.2, trend: 'up', stories: 9,
    sectors: [
      { key: 'energy', index: 60, prev_index: 40, delta: 20, trend: 'up' },
      { key: 'aviation', index: 30, prev_index: 25, delta: 5, trend: 'up' },
      { key: 'security', index: 50, prev_index: 55, delta: -5, trend: 'down' },
    ],
    top_events: [
      { id: 1, title: 'Duplicate of a top story', url: 'https://ok.test/a', ksa_impact: 80 },
      { id: 9, title: 'Houthi drone attack on Aramco facility', url: 'https://ok.test/k', ksa_impact: 90 },
    ],
  },
  chains: [{
    length: 1,
    confidence: 0.62,
    nodes: [
      { id: 21, title: 'Israel strikes targets in Iran', url: 'https://ok.test/c1' },
      { id: 22, title: 'Iran launches retaliatory strikes on Israel', url: 'javascript:alert(2)' },
    ],
    links: [{ id: 5, confidence: 0.62 }],
  }],
  narrative_method: 'template',
};

describe('narrative summary', () => {
  beforeAll(async () => { await i18n.changeLanguage('en'); });

  it('builds the opening paragraph from templates', () => {
    const text = narrativeText(buildNarrative(narrativeBrief, t));
    expect(text).toContain('The nuclear & radiological risk index is 44.6 (Moderate), up 3.1 on the previous period (was 41.5).');
    expect(text).toContain('The Kingdom impact index is 62.3 (High), up 12.2 on the previous period (was 50.1).');
    expect(text).toContain('Top nuclear & radiological stories: “Strike <script>alert(1)</script> on Natanz” (E1), “Bad link” (E2).');
    // قصة مذكورة أعلاه لا تتكرّر في «الأعلى أثرًا»
    expect(text).toContain('Highest impact on the Kingdom: “Houthi drone attack on Aramco facility” (E9).');
    expect(text).toContain('Rising sectors: Energy (+20.0), Aviation (+5.0).');
    expect(text).toContain('Notable chains: “Israel strikes targets in Iran” (E21) → “Iran launches retaliatory strikes on Israel” (E22) (62% confidence).');
  });

  it('cites events as structured segments, with direction-isolated titles', () => {
    const segs = buildNarrative(narrativeBrief, t).flat();
    expect(segs.filter(s => s.type === 'cite').map(s => s.id)).toEqual([1, 2, 9, 21, 22]);
    expect(segs.filter(s => s.type === 'title').map(s => s.text)).toContain('Israel strikes targets in Iran');
  });

  it('lists each cited event once, with safe URLs only', () => {
    const notes = narrativeNotes(buildNarrative(narrativeBrief, t));
    expect(notes.map(n => n.id)).toEqual([1, 2, 9, 21, 22]);
    expect(notes.find(n => n.id === 2).url).toBeFalsy();
    expect(notes.find(n => n.id === 22).url).toBeFalsy();
    expect(notes.find(n => n.id === 21).url).toBe('https://ok.test/c1');
  });

  it('handles quiet periods and older briefs', () => {
    const quiet = narrativeText(buildNarrative({
      ...brief, top_stories: [],
      ksa_impact: { index: 0, level: 'low', prev_index: 0, delta: 0, trend: 'flat', sectors: [], top_events: [] },
      chains: [],
    }, t));
    expect(quiet).toContain('little changed on the previous period');
    expect(quiet).toContain('No notable nuclear or radiological stories in the period.');
    expect(quiet).toContain("No sector's impact rose clearly on the previous period.");
    expect(quiet).toContain('No chains above the confidence threshold in the period.');
    // تقرير بلا حقول الموجز الجديدة (خادم أقدم): جملة المؤشر النووي والقصص فقط
    const old = buildNarrative(brief, t);
    expect(old).toHaveLength(2);
    expect(buildNarrative(null, t)).toEqual([]);
  });

  it('builds the Arabic paragraph', async () => {
    await i18n.changeLanguage('ar');
    const text = narrativeText(buildNarrative(narrativeBrief, t));
    expect(text).toContain('مؤشر الأثر على المملكة 62.3 (مرتفع)، مرتفعًا 12.2 عن الفترة السابقة (كان 50.1).');
    expect(text).toContain('القطاعات الصاعدة: طاقة (+20.0)، طيران (+5.0).');
    expect(text).toContain('«Israel strikes targets in Iran» (E21) ← «Iran launches retaliatory strikes on Israel» (E22) (ثقة 62%)');
    await i18n.changeLanguage('en');
  });

  it('shortens long titles', () => {
    expect(shortTitle('x'.repeat(200), 10)).toBe(`${'x'.repeat(9)}…`);
    expect(shortTitle(' short ')).toBe('short');
  });
});

describe('report export', () => {
  beforeAll(async () => { await i18n.changeLanguage('en'); });

  it('summarises index, level, trend and counts', () => {
    expect(summaryLine(brief, t)).toBe(
      'Index 44.6 (Moderate), Up 3.1 on the previous period. 26 stories from 32 reports, 1 of them near the Kingdom.',
    );
  });

  it('builds markdown with safe links only', () => {
    const md = toMarkdown(brief, t, 'en');
    expect(md).toContain('# Nuclear & radiological watch report');
    expect(md).toContain('[Strike <script>alert(1)</script> on Natanz](https://ok.test/a)');
    expect(md).not.toContain('javascript:');
    expect(md).toContain('Natanz: 1 stories, Risk score 79');
  });

  it('puts the narrative first, with plain E<id> citations and a reference list', () => {
    const md = toMarkdown(narrativeBrief, t, 'en');
    expect(md.indexOf('## Overview')).toBeGreaterThan(0);
    expect(md.indexOf('## Overview')).toBeLessThan(md.indexOf('## Summary'));
    expect(md).toContain('(E21) → “Iran launches');
    expect(md).not.toMatch(/\[E\d+\]\(/);                       // الاستشهاد نص لا رابط
    expect(md).toContain('### Event references');
    expect(md).toContain('1. **E1** — Strike <script>alert(1)</script> on Natanz — <https://ok.test/a>');
    expect(md).toContain('2. **E2** — Bad link\n');
    expect(md).not.toContain('javascript:');
  });

  it('builds a standalone, escaped HTML document', () => {
    const html = toHtml(brief, t, 'ar');
    expect(html.startsWith('<!doctype html>')).toBe(true);
    expect(html).toContain('dir="rtl"');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('javascript:');
    expect(html).not.toMatch(/<script|<link|src=/);           // بلا موارد خارجية
  });

  it('exports the narrative as escaped plain text with footnoted URLs', () => {
    const html = toHtml(narrativeBrief, t, 'en');
    expect(html).toContain('<section class="narrative">');
    expect(html).toContain('(E21) → “<bdi>Iran launches retaliatory strikes on Israel</bdi>” (E22)');
    expect(html).toContain('<bdi>Strike &lt;script&gt;alert(1)&lt;/script&gt; on Natanz</bdi>');
    expect(html).toContain('<li><b>E21</b> — Israel strikes targets in Iran — <a href="https://ok.test/c1">https://ok.test/c1</a></li>');
    expect(html).toContain('<li><b>E22</b> — Iran launches retaliatory strikes on Israel</li>');
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('<script>');
    expect(html.indexOf('class="narrative"')).toBeLessThan(html.indexOf('class="index"'));
  });
});
