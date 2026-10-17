import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import i18n from '../../i18n';
import StatsPanel from './StatsPanel';

const stats = {
  total: 1250,
  categories: { military: 400, nuclear: 50, diplomatic: 300 },
  countries: [
    { code: 'IR', name: 'Iran', count: 500 },
    { code: 'XX', name: 'Elsewhere', count: 20 },
  ],
  sources: { rss: 900, gdelt: 350 },
  escalation_index: 32.5,
  escalation_delta: 4.2,
  escalation_series: [{ value: 20 }, { value: 25 }, { value: 32.5 }],
};

describe('<StatsPanel>', () => {
  beforeEach(async () => { await i18n.changeLanguage('en'); });

  it('shows a loading placeholder before the first response', () => {
    render(<StatsPanel stats={null} />);
    expect(screen.getByLabelText('Loading…')).toHaveAttribute('aria-busy', 'true');
  });

  it('shows the escalation index with its trend and the totals', () => {
    render(<StatsPanel stats={stats} countryIndex={null} />);
    expect(screen.getByText('32.5%')).toBeInTheDocument();
    expect(screen.getByText(/Up 4\.2/)).toBeInTheDocument();
    expect(screen.getByText('1.3K')).toBeInTheDocument();   // formatNumber
    expect(screen.getByText('400', { selector: '.text-red-400' })).toBeInTheDocument();
  });

  it('lists countries (with a fallback name) and sources', () => {
    render(<StatsPanel stats={stats} countryIndex={null} />);
    expect(screen.getByText('Elsewhere')).toBeInTheDocument();
    expect(screen.getByText('rss')).toBeInTheDocument();
    expect(screen.getByText('900')).toBeInTheDocument();
  });

  it('says there is no comparison when the trend is unknown', () => {
    render(<StatsPanel stats={{ ...stats, escalation_delta: null }} countryIndex={null} />);
    expect(screen.getByText('No comparison: previous period is beyond data retention')).toBeInTheDocument();
  });
});
