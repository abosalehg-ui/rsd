import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import i18n from '../../i18n';
import KsaLens from './KsaLens';
import ImpactBreakdown from './ImpactBreakdown';
import * as api from '../../utils/api';

const aramco = {
  id: 11,
  title: 'Houthi drone attack on Aramco facility in Abqaiq',
  category: 'military',
  severity: 'critical',
  ksa_impact: 90,
  impact_sectors: ['security', 'energy'],
  impact: {
    score: 90,
    components: { severity: 1, proximity: 1, mention: 1, source_trust: 0.9 },
    severity: 'critical',
    proximity_band: 'adjacent',
    distance_to_ksa_km: 12.4,
    nearest_ksa_point: 'الأحساء',
    nearest_ksa_point_en: 'Al-Ahsa',
    mention: 'asset',
    mentioned: ['aramco'],
  },
  event_date: new Date().toISOString(),
};

const sector = (key, index, extra = {}) => ({
  key, index, prev_index: 0, delta: index, trend: 'up', stories: index ? 2 : 0, max: index, top_event_id: null, ...extra,
});

const impact = {
  period_hours: 48,
  index: 77.6,
  level: 'critical',
  prev_index: 40.2,
  delta: 37.4,
  trend: 'up',
  stories: 4,
  events: 5,
  components: { max: 90, top_mean: 59.2, max_weight: 0.6, top_mean_weight: 0.4, top_n: 10 },
  series: [{ value: 10 }, { value: 40 }, { value: 77.6 }],
  sectors: [
    sector('security', 70.1, { top_event_id: 11 }),
    sector('energy', 54, { top_event_id: 11 }),
    sector('health', 0),
  ],
  watch: [{ key: 'energy', index: 54, prev_index: 0, delta: 54, stories: 1, top_event_id: 11 }],
  top_events: [aramco],
  formula: {
    max_weight: 0.6, top_mean_weight: 0.4, top_n: 10,
    severity: { critical: 1, high: 0.75, medium: 0.5, low: 0.25 },
    proximity: { adjacent: 1, near: 0.8, regional: 0.55, far: 0.3, unknown: 0.45 },
    mention: { asset: 1, ksa: 0.9, chokepoint: 0.85, none: 0.6 },
    source_trust: { official: 1, news: 0.9 },
    watch_min_delta: 10,
    watch_min_index: 25,
  },
};

describe('<KsaLens>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });

  it('shows the index on the shared gauge with its formula', async () => {
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    render(<KsaLens />);
    expect(await screen.findByText('77.6')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Kingdom impact index' })).toBeInTheDocument();
    expect(screen.getAllByText('Critical')[0]).toBeInTheDocument();
    expect(screen.getByText(
      /60% of the highest single impact \(90\) \+ 40% of the mean of the top 10 stories \(59.2\)/,
    )).toBeInTheDocument();
  });

  it('lists rule-based watch items and opens their top event', async () => {
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    const onOpenEvent = vi.fn();
    render(<KsaLens onOpenEvent={onOpenEvent} />);
    const watch = within(await screen.findByRole('region', { name: 'Watch' }));
    expect(watch.getByText('Energy')).toBeInTheDocument();
    expect(watch.getByText('Up from 0.0 to 54.0')).toBeInTheDocument();
    expect(watch.getByText(/rises 10 points or more on the previous period and reaches 25/)).toBeInTheDocument();
    fireEvent.click(watch.getByRole('button', { name: aramco.title }));
    expect(onOpenEvent).toHaveBeenCalledWith(aramco);
  });

  it('fetches a watch item event that is not among the top events', async () => {
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue({
      ...impact, watch: [{ ...impact.watch[0], top_event_id: 99 }],
    });
    const other = { ...aramco, id: 99, title: 'Other' };
    const getEvent = vi.spyOn(api, 'getEvent').mockResolvedValue(other);
    const onOpenEvent = vi.fn();
    render(<KsaLens onOpenEvent={onOpenEvent} />);
    const watch = within(await screen.findByRole('region', { name: 'Watch' }));
    fireEvent.click(watch.getByRole('button', { name: 'Open the top event' }));
    await waitFor(() => expect(onOpenEvent).toHaveBeenCalledWith(other));
    expect(getEvent).toHaveBeenCalledWith(99);
  });

  it('shows the sector bars and filters the feed by sector', async () => {
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    const onSelectSector = vi.fn();
    render(<KsaLens onSelectSector={onSelectSector} />);
    const bars = within(await screen.findByRole('region', { name: 'Impact by sector' }));
    fireEvent.click(bars.getByRole('button', { name: 'Security: 70.1 — 2 stories' }));
    expect(onSelectSector).toHaveBeenCalledWith('security');
    expect(bars.getByRole('button', { name: 'Health: 0.0 — 0 stories' })).toBeInTheDocument();
  });

  it('shows each top event with its own formula and opens it', async () => {
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    const onOpenEvent = vi.fn();
    render(<KsaLens onOpenEvent={onOpenEvent} />);
    const top = within(await screen.findByRole('region', { name: 'Highest-impact events' }));
    expect(top.getByText('90.0 = 100 × 1 × 1 × 1 × 0.9')).toBeInTheDocument();
    fireEvent.click(top.getByText(aramco.title));
    expect(onOpenEvent).toHaveBeenCalledWith(aramco);
  });

  it('explains the formula factors', async () => {
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    render(<KsaLens />);
    await screen.findByText('77.6');
    const table = screen.getByRole('table', { name: 'Direct mention' });
    expect(within(table).getByText('Critical Saudi asset')).toBeInTheDocument();
    expect(within(table).getByText('×0.6')).toBeInTheDocument();
  });

  it('refetches when the period changes', async () => {
    const spy = vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    render(<KsaLens />);
    await screen.findByText('77.6');
    expect(spy).toHaveBeenLastCalledWith(48);
    fireEvent.change(screen.getByLabelText('Period'), { target: { value: '72' } });
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(72));
  });

  it('shows a retryable error', async () => {
    vi.spyOn(api, 'getKsaImpact').mockRejectedValue(new Error('down'));
    render(<KsaLens />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/Couldn't load the impact index/);
  });

  it('renders correctly in Arabic (RTL labels)', async () => {
    await i18n.changeLanguage('ar');
    vi.spyOn(api, 'getKsaImpact').mockResolvedValue(impact);
    render(<KsaLens />);
    expect(await screen.findByRole('heading', { name: 'مؤشر الأثر على المملكة' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'راقِب' })).toBeInTheDocument();
    // المعادلة أرقام: تبقى LTR داخل الواجهة العربية
    expect(screen.getByText('90.0 = 100 × 1 × 1 × 1 × 0.9')).toHaveAttribute('dir', 'ltr');
  });
});

describe('<ImpactBreakdown>', () => {
  beforeEach(async () => { await i18n.changeLanguage('en'); });

  it('explains every factor with its reason', () => {
    render(<ImpactBreakdown event={aramco} />);
    expect(screen.getByText('Impact on the Kingdom', { selector: 'h3' })).toBeInTheDocument();
    expect(screen.getByText('Adjacent (under 300 km) — 12 km from Al-Ahsa')).toBeInTheDocument();
    expect(screen.getByText('Critical Saudi asset — aramco')).toBeInTheDocument();
    expect(screen.getByText('×0.9')).toBeInTheDocument();
    expect(screen.getByText('Energy')).toBeInTheDocument();
  });

  it('renders nothing for events without impact data', () => {
    const { container } = render(<ImpactBreakdown event={{ id: 1 }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says when no sector was tagged', () => {
    render(<ImpactBreakdown event={{ ...aramco, impact_sectors: [] }} />);
    expect(screen.getByText('No sector tagged')).toBeInTheDocument();
  });
});
