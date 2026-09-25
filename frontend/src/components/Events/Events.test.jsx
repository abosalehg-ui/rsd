import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '../../i18n';
import i18n from '../../i18n';
import EventCard from './EventCard';
import EventDrawer from './EventDrawer';
import { timeGroup } from './StoryList';

const nuclearStory = {
  id: 7,
  title: 'Missile strike on Bushehr nuclear power plant',
  description: 'Officials report damage.',
  category: 'nuclear',
  severity: 'critical',
  topic: 'military_threat',
  risk_score: 85.5,
  country_code: 'IR',
  country: 'إيران',
  geo_precision: 'facility',
  facility_id: 'ir-bushehr-1',
  latitude: 28.8,
  longitude: 50.9,
  source: 'nuclear_watch',
  source_name: 'Reuters',
  url: 'https://example.com/a',
  event_date: new Date().toISOString(),
  story_source_count: 3,
  story_related: [
    { id: 8, title: 'Bushehr hit', source_name: 'AP', url: 'https://example.com/b', event_date: new Date().toISOString() },
    { id: 9, title: 'Bushehr plant struck', source_name: 'Evil', url: 'javascript:alert(1)', event_date: new Date().toISOString() },
  ],
  nuclear: {
    components: { base: 75, intensity: 0, dampening: 0, reassurance: 0, statement: 0, specificity: 5, proximity: 15, source_trust: 0.9 },
    distance_to_ksa_km: 235.4,
    nearest_ksa_point: 'الجبيل',
  },
  extra: {},
};

describe('<EventCard>', () => {
  it('shows topic, source count and risk score', async () => {
    await i18n.changeLanguage('en');
    render(<EventCard event={nuclearStory} />);
    expect(screen.getByText('Military threat to a nuclear site')).toBeInTheDocument();
    expect(screen.getByText('3 sources')).toBeInTheDocument();
    expect(screen.getByTitle('Risk score')).toHaveTextContent('86');
  });

  it('marks country-level locations as approximate', async () => {
    await i18n.changeLanguage('en');
    render(<EventCard event={{ ...nuclearStory, geo_precision: 'country' }} />);
    expect(screen.getByLabelText('Approximate location')).toBeInTheDocument();
  });

  it('opens on Enter', () => {
    const onOpen = vi.fn();
    render(<EventCard event={nuclearStory} onOpen={onOpen} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' });
    expect(onOpen).toHaveBeenCalledWith(nuclearStory);
  });
});

describe('<EventDrawer>', () => {
  it('lists every source with safe links only', async () => {
    await i18n.changeLanguage('en');
    render(<EventDrawer event={nuclearStory} onClose={() => {}} />);
    const hrefs = screen.getAllByRole('link').map(a => a.getAttribute('href'));
    expect(hrefs).toContain('https://example.com/a');
    expect(hrefs).toContain('https://example.com/b');
    expect(hrefs.some(h => h.startsWith('javascript'))).toBe(false);
    expect(screen.getByText('Evil')).toBeInTheDocument();       // المصدر يظهر بلا رابط
  });

  it('explains the score and distance to the Kingdom', async () => {
    await i18n.changeLanguage('en');
    render(<EventDrawer event={nuclearStory} onClose={() => {}} />);
    expect(screen.getByText('Proximity to the Kingdom')).toBeInTheDocument();
    expect(screen.getByText('+15')).toBeInTheDocument();
    expect(screen.getByText('×0.9')).toBeInTheDocument();
    expect(screen.getByText(/235 km from/)).toBeInTheDocument();
  });

  it('closes on Escape and offers "show on map"', async () => {
    await i18n.changeLanguage('en');
    const onClose = vi.fn();
    const onShowOnMap = vi.fn();
    render(<EventDrawer event={nuclearStory} onClose={onClose} onShowOnMap={onShowOnMap} />);
    fireEvent.click(screen.getByText('Show on map'));
    expect(onShowOnMap).toHaveBeenCalledWith(nuclearStory);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('renders nothing without an event', () => {
    const { container } = render(<EventDrawer event={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('timeGroup', () => {
  const now = new Date(2026, 8, 25, 15, 0, 0);
  it.each([
    [new Date(2026, 8, 25, 14, 30), 'hour'],
    [new Date(2026, 8, 25, 2, 0), 'today'],
    [new Date(2026, 8, 24, 22, 0), 'yesterday'],
    [new Date(2026, 8, 20, 10, 0), 'older'],
  ])('%s → %s', (date, group) => {
    expect(timeGroup(date.toISOString(), now)).toBe(group);
  });
});
