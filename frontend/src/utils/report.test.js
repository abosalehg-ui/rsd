import { describe, it, expect, beforeAll } from 'vitest';
import i18n from '../i18n';
import { summaryLine, toHtml, toMarkdown } from './report';

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

  it('builds a standalone, escaped HTML document', () => {
    const html = toHtml(brief, t, 'ar');
    expect(html.startsWith('<!doctype html>')).toBe(true);
    expect(html).toContain('dir="rtl"');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('javascript:');
    expect(html).not.toMatch(/<script|<link|src=/);           // بلا موارد خارجية
  });
});
