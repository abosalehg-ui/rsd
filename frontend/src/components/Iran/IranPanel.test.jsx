import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import i18n from '../../i18n';
import * as api from '../../utils/api';
import IranPanel from './IranPanel';

const strikes = [
  { id: 1, title: 'Strike near Isfahan', confidence: 'HIGH', event_type: 'strike', location_name: 'Isfahan', url: 'https://ok.test/1', video_url: 'https://ok.test/v' },
  { id: 2, title: 'Drills in the Gulf', confidence: 'MEDIUM', event_type: 'movement', country: 'IR', url: 'javascript:alert(1)' },
  { id: 3, title: 'Unverified launch claim', confidence: 'LOW', event_type: 'launch' },
];

const leaders = [
  { id: 1, name: 'Leader One', role: 'Role A', icon: '👤', active: true, recent_news: [{ title: 'News A', url: 'https://ok.test/n' }] },
  { id: 2, name: 'Leader Two', role: 'Role B', icon: '👤', active: false, recent_news: [] },
];

describe('<IranPanel>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
    vi.spyOn(api, 'getIranLeaders').mockResolvedValue({ leaders });
    vi.spyOn(api, 'getIranStats').mockResolvedValue({ total: 3, by_confidence: { HIGH: 1 }, by_type: { strike: 1 } });
  });

  it('lists strikes with stats and opens one on click and Enter', async () => {
    const onSelectStrike = vi.fn();
    render(<IranPanel strikes={strikes} onSelectStrike={onSelectStrike} />);
    expect(await screen.findByText('Total')).toBeInTheDocument();
    expect(screen.getByText('Strike near Isfahan')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Strike near Isfahan'));
    expect(onSelectStrike).toHaveBeenCalledWith(strikes[0]);
    fireEvent.keyDown(screen.getByText('Drills in the Gulf').closest('[role="button"]'), { key: 'Enter' });
    expect(onSelectStrike).toHaveBeenCalledWith(strikes[1]);
  });

  it('only links safe URLs', async () => {
    render(<IranPanel strikes={strikes} />);
    await screen.findByText('Total');
    const sources = screen.getAllByRole('link', { name: 'Source →' });
    expect(sources).toHaveLength(1);
    expect(sources[0]).toHaveAttribute('href', 'https://ok.test/1');
    expect(screen.getByRole('link', { name: '🎥 Video' })).toHaveAttribute('href', 'https://ok.test/v');
  });

  it('filters by confidence with 44px chips', async () => {
    render(<IranPanel strikes={strikes} />);
    await screen.findByText('Total');
    const chip = screen.getByRole('button', { name: '🔵 Unverified' });
    expect(chip.className).toContain('min-h-11');
    fireEvent.click(chip);
    expect(chip).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Unverified launch claim')).toBeInTheDocument();
    expect(screen.queryByText('Strike near Isfahan')).not.toBeInTheDocument();
  });

  it('shows leaders and their news in the leaders tab', async () => {
    render(<IranPanel strikes={[]} />);
    fireEvent.click(screen.getByRole('tab', { name: /Leaders/ }));
    const panel = await screen.findByRole('tabpanel');
    expect(await within(panel).findByText('Leader One')).toBeInTheDocument();
    expect(within(panel).getByText('active')).toBeInTheDocument();
    expect(within(panel).getByRole('link', { name: /News A/ })).toHaveAttribute('href', 'https://ok.test/n');
  });

  it('reports a failed load with a retry', async () => {
    api.getIranLeaders.mockRejectedValue(new Error('down'));
    render(<IranPanel strikes={[]} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load Iran data');
    expect(screen.getByText('No data')).toBeInTheDocument();
  });
});
