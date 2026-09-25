import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import i18n from '../../i18n';
import RiskGauge from './RiskGauge';
import NuclearPanel from './NuclearPanel';
import * as api from '../../utils/api';

const risk = {
  index: 61.9,
  level: 'high',
  prev_index: 58.2,
  delta: 3.7,
  stories: 27,
  near_ksa_stories: 2,
  components: { max: 66.3, top_mean: 55.3, max_weight: 0.6, top_mean_weight: 0.4, top_n: 5 },
  series: [{ value: 40 }, { value: 50 }, { value: 61.9 }],
  by_topic: { military_threat: { stories: 3, max_risk: 66.3 }, safeguards_iaea: { stories: 2, max_risk: 35 } },
};

describe('<RiskGauge>', () => {
  beforeEach(async () => { await i18n.changeLanguage('en'); });

  it('shows the value with its level and trend', () => {
    render(<RiskGauge risk={risk} />);
    expect(screen.getByText('61.9')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Up 3.7 on the previous period')).toBeInTheDocument();
    expect(screen.getByText('2 near the Kingdom')).toBeInTheDocument();
  });

  it('explains the formula with the real numbers', () => {
    render(<RiskGauge risk={risk} />);
    expect(screen.getByText(/60% of the highest single risk \(66.3\) \+ 40% of the mean of the top 5 stories \(55.3\)/)).toBeInTheDocument();
  });

  it('shows a retryable error when the index failed to load', () => {
    const onRetry = vi.fn();
    render(<RiskGauge risk={null} error="down" onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('reports a drop in green terms', () => {
    render(<RiskGauge risk={{ ...risk, delta: -4 }} />);
    expect(screen.getByText('Down 4.0 on the previous period')).toBeInTheDocument();
  });
});

describe('<NuclearPanel>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });

  it('loads stories and filters by topic', async () => {
    const getEvents = vi.spyOn(api, 'getNuclearEvents').mockResolvedValue({
      events: [{
        id: 1, title: 'Strike near Natanz', category: 'nuclear', severity: 'high', topic: 'military_threat',
        risk_score: 66, event_date: new Date().toISOString(), source_name: 'X',
      }],
    });
    vi.spyOn(api, 'getFacilityWatch').mockResolvedValue({ facilities: [] });

    render(<NuclearPanel risk={risk} hours={24} />);
    expect(await screen.findByText('Strike near Natanz')).toBeInTheDocument();
    expect(screen.getByText('No facility was named in this period.')).toBeInTheDocument();

    const chips = within(screen.getByRole('group', { name: 'By topic' }));
    fireEvent.click(chips.getByRole('button', { name: /Military threat to a nuclear site/ }));
    await waitFor(() => expect(getEvents).toHaveBeenLastCalledWith(expect.objectContaining({ topic: 'military_threat' })));

    fireEvent.click(screen.getByLabelText(/Near the Kingdom only/));
    await waitFor(() => expect(getEvents).toHaveBeenLastCalledWith(expect.objectContaining({ near_ksa_km: 800 })));
  });

  it('lists facilities in the news with distance to the Kingdom', async () => {
    vi.spyOn(api, 'getNuclearEvents').mockResolvedValue({ events: [] });
    vi.spyOn(api, 'getFacilityWatch').mockResolvedValue({
      facilities: [{
        facility_id: 'ir-bushehr-1', name_en: 'Bushehr-1', name_ar: 'بوشهر', country_code: 'IR',
        max_risk: 85, stories: 2, distance_to_ksa_km: 235.4, nearest_ksa_point: 'الجبيل', nearest_ksa_point_en: 'Jubail',
      }],
    });
    const onSelectFacility = vi.fn();
    render(<NuclearPanel risk={risk} hours={24} onSelectFacility={onSelectFacility} />);
    const row = await screen.findByText('Bushehr-1');
    expect(screen.getByText('235 km from Jubail')).toBeInTheDocument();
    fireEvent.click(row);
    expect(onSelectFacility).toHaveBeenCalled();
  });
});
