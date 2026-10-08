import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import i18n from '../../i18n';
import * as api from '../../utils/api';
import ReportView from './ReportView';

const brief = {
  period_hours: 24,
  generated_at: '2026-10-08T12:00:00Z',
  risk: { index: 44.6, level: 'medium', delta: 3.1, prev_index: 41.5, stories: 2, near_ksa_stories: 0 },
  totals: { events: 3, stories: 2 },
  top_stories: [{ id: 1, title: 'Strike on Natanz', url: 'https://ok.test/a', risk_score: 79, topic: 'military_threat', source_name: 'Reuters' }],
  near_ksa: [], incidents: [], political: [], facilities: [], sources: { Reuters: 1 },
  ksa_impact: {
    index: 62.3, level: 'high', prev_index: 50.1, delta: 12.2, trend: 'up', stories: 4,
    sectors: [{ key: 'energy', index: 60, prev_index: 40, delta: 20, trend: 'up' }], top_events: [],
  },
  chains: [{
    length: 1, confidence: 0.62,
    nodes: [{ id: 21, title: 'Israel strikes targets in Iran' }, { id: 22, title: 'Iran retaliates' }],
    links: [{ id: 5, confidence: 0.62 }],
  }],
  narrative_method: 'template',
};

describe('<ReportView> narrative', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });

  it('opens with the template summary and links each citation to its event', async () => {
    vi.spyOn(api, 'getNuclearBrief').mockResolvedValue(brief);
    const onOpenEvent = vi.fn();
    render(<ReportView open onClose={() => {}} onOpenEvent={onOpenEvent} />);
    const summary = within(await screen.findByRole('region', { name: 'Overview' }));
    expect(summary.getByText(/The Kingdom impact index is 62.3 \(High\)/)).toBeInTheDocument();
    expect(summary.getByText(/Rising sectors: Energy \(\+20.0\)/)).toBeInTheDocument();
    expect(summary.getByText(/no AI wording/)).toBeInTheDocument();

    const cite = summary.getByRole('link', { name: 'Open event E21' });
    expect(cite).toHaveTextContent('E21');
    expect(cite.getAttribute('href')).toMatch(/\?event=21$/);
    fireEvent.click(cite);
    expect(onOpenEvent).toHaveBeenCalledWith(21);
    expect(summary.getAllByRole('link').map(a => a.textContent)).toEqual(['E1', 'E21', 'E22']);
  });

  it('keeps the plain deep link when no handler is given', async () => {
    vi.spyOn(api, 'getNuclearBrief').mockResolvedValue(brief);
    render(<ReportView open onClose={() => {}} />);
    const summary = within(await screen.findByRole('region', { name: 'Overview' }));
    const cite = summary.getByRole('link', { name: 'Open event E1' });
    expect(fireEvent.click(cite)).toBe(true);            // لم يُمنع السلوك الافتراضي
  });
});
